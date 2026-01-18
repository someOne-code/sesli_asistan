"""
Business Layer (İş Mantığı Katmanı)
====================================
İş kurallarını, validasyonları ve iş mantığını içerir.
Data Access Layer ile Presentation Layer arasında köprü görevi görür.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from config import logger, LogEmoji


class MusicCatalogBusiness:
    """
    Müzik Kataloğu İş Mantığı
    Tüm iş kuralları ve validasyonları burada
    """
    
    # İş Kuralları - Sabitler
    MIN_PRICE = 0.0
    MAX_PRICE = 100.0
    DEFAULT_LIMIT = 5
    MAX_LIMIT = 20
    MIN_SEARCH_LENGTH = 2
    POPULAR_GENRES = ['Rock', 'Jazz', 'Pop', 'Classical', 'Metal', 'Blues']
    
    def __init__(self, data_service):
        """
        Args:
            data_service: SafeService (Data Access Layer)
        """
        self.data_service = data_service
        logger.info(f"{LogEmoji.CHECK} MusicCatalogBusiness initialized")
    
    # ==================== VALIDATION METHODS ====================
    
    def validate_search_keyword(self, keyword: str) -> tuple[bool, str]:
        """
        Arama kelimesini doğrula
        
        Returns:
            (geçerli_mi, hata_mesajı)
        """
        if not keyword or len(keyword.strip()) < self.MIN_SEARCH_LENGTH:
            return False, f"Arama kelimesi en az {self.MIN_SEARCH_LENGTH} karakter olmalı"
        
        if len(keyword) > 100:
            return False, "Arama kelimesi çok uzun (max 100 karakter)"
        
        return True, ""
    
    def validate_limit(self, limit: int) -> int:
        """
        Limit değerini doğrula ve güvenli değere ayarla
        
        Returns:
            Güvenli limit değeri
        """
        if limit < 1:
            return self.DEFAULT_LIMIT
        
        if limit > self.MAX_LIMIT:
            return self.MAX_LIMIT
        
        return limit
    
    def validate_price_range(self, min_price: float, max_price: float) -> tuple[bool, str]:
        """
        Fiyat aralığını doğrula
        
        Returns:
            (geçerli_mi, hata_mesajı)
        """
        if min_price < self.MIN_PRICE:
            return False, f"Minimum fiyat {self.MIN_PRICE} TL'den küçük olamaz"
        
        if max_price > self.MAX_PRICE:
            return False, f"Maximum fiyat {self.MAX_PRICE} TL'den büyük olamaz"
        
        if min_price > max_price:
            return False, "Minimum fiyat, maximum fiyattan büyük olamaz"
        
        return True, ""
    
    # ==================== BUSINESS LOGIC METHODS ====================
    
    def search_music(self, keyword: str, search_type: str = 'all', limit: int = 5) -> Dict:
        """
        Müzik ara - İş mantığı ile
        
        Args:
            keyword: Arama kelimesi
            search_type: 'all', 'tracks', 'albums', 'artists'
            limit: Sonuç sayısı
            
        Returns:
            İş mantığı ile zenginleştirilmiş sonuçlar
        """
        # 1. Validasyon
        is_valid, error_msg = self.validate_search_keyword(keyword)
        if not is_valid:
            return {
                'status': 'error',
                'error': 'VALIDATION_ERROR',
                'message': error_msg
            }
        
        limit = self.validate_limit(limit)
        
        # 2. Arama tipine göre dal
        results = {'status': 'success', 'data': {}}
        
        if search_type in ['all', 'tracks']:
            track_result = self.data_service.execute_action(
                'SEARCH_TRACKS',
                {'keyword': keyword, 'limit': limit}
            )
            results['data']['tracks'] = track_result.get('data', [])
        
        if search_type in ['all', 'albums']:
            album_result = self.data_service.execute_action(
                'SEARCH_ALBUMS',
                {'keyword': keyword, 'limit': limit}
            )
            results['data']['albums'] = album_result.get('data', [])
        
        if search_type in ['all', 'artists']:
            artist_result = self.data_service.execute_action(
                'SEARCH_ARTISTS',
                {'keyword': keyword, 'limit': limit}
            )
            results['data']['artists'] = artist_result.get('data', [])
        
        # 3. İş mantığı - Sonuçları zenginleştir
        results = self._enrich_search_results(results, keyword)
        
        return results
    
    def get_recommendations_by_genre(self, genre: str, user_preferences: Dict = None) -> Dict:
        """
        Türe göre öneri al - İş kuralları ile
        
        Args:
            genre: Müzik türü
            user_preferences: Kullanıcı tercihleri (fiyat aralığı, vb.)
            
        Returns:
            Öneriler
        """
        limit = self.DEFAULT_LIMIT
        
        # İş kuralı: Popüler türler için daha fazla sonuç
        if genre in self.POPULAR_GENRES:
            limit = 10
        
        # Kullanıcı tercihleri varsa uygula
        if user_preferences:
            limit = self.validate_limit(user_preferences.get('limit', limit))
        
        # Data layer'dan veri al
        result = self.data_service.execute_action(
            'GET_TRACKS_BY_GENRE',
            {'genre_name': genre, 'limit': limit}
        )
        
        if result['status'] == 'success':
            # İş mantığı: Fiyata göre sırala ve kategorize et
            tracks = result['data']
            categorized = self._categorize_by_price(tracks)
            
            return {
                'status': 'success',
                'genre': genre,
                'is_popular_genre': genre in self.POPULAR_GENRES,
                'recommendations': categorized
            }
        
        return result
    
    def get_budget_friendly_tracks(self, genre: Optional[str] = None, max_price: float = 1.0) -> Dict:
        """
        Bütçe dostu parçalar - İş kuralı
        
        Args:
            genre: Tür (opsiyonel)
            max_price: Maximum fiyat
            
        Returns:
            Uygun fiyatlı parçalar
        """
        # İş kuralı: Bütçe dostu = en ucuz parçalar
        result = self.data_service.execute_action(
            'GET_CHEAPEST_TRACKS',
            {'limit': 10, 'genre': genre}
        )
        
        if result['status'] == 'success':
            tracks = result['data']
            
            # İş mantığı: Sadece max_price altındakileri filtrele
            budget_tracks = [
                track for track in tracks 
                if track.get('UnitPrice', 999) <= max_price
            ]
            
            # İş mantığı: Tasarruf hesapla
            if budget_tracks:
                avg_price = sum(t['UnitPrice'] for t in budget_tracks) / len(budget_tracks)
                total_savings = (max_price - avg_price) * len(budget_tracks)
                
                return {
                    'status': 'success',
                    'tracks': budget_tracks,
                    'count': len(budget_tracks),
                    'average_price': round(avg_price, 2),
                    'estimated_savings': round(total_savings, 2),
                    'message': f"{len(budget_tracks)} adet uygun fiyatlı parça bulundu"
                }
            else:
                return {
                    'status': 'success',
                    'tracks': [],
                    'count': 0,
                    'message': f"{max_price} TL altında parça bulunamadı"
                }
        
        return result
    
    def get_premium_collection(self, genre: Optional[str] = None) -> Dict:
        """
        Premium koleksiyon - İş mantığı
        Yüksek kaliteli (pahalı) parçalar
        """
        result = self.data_service.execute_action(
            'GET_MOST_EXPENSIVE_TRACKS',
            {'limit': 10, 'genre': genre}
        )
        
        if result['status'] == 'success':
            tracks = result['data']
            
            return {
                'status': 'success',
                'collection': 'premium',
                'tracks': tracks,
                'count': len(tracks),
                'message': "Premium koleksiyonumuzdan seçkiler"
            }
        
        return result
    
    def get_artist_profile(self, artist_name: str) -> Dict:
        """
        Sanatçı profili - İş mantığı ile zenginleştirilmiş
        
        Args:
            artist_name: Sanatçı adı
            
        Returns:
            Detaylı sanatçı bilgisi
        """
        # 1. Sanatçının albümlerini al
        albums_result = self.data_service.execute_action(
            'GET_ARTIST_ALBUMS',
            {'artist_name': artist_name, 'limit': 20}
        )
        
        if albums_result['status'] != 'success' or not albums_result['data']:
            return {
                'status': 'error',
                'error': 'ARTIST_NOT_FOUND',
                'message': f"{artist_name} bulunamadı"
            }
        
        albums = albums_result['data']
        
        # 2. İş mantığı: Profil oluştur
        profile = {
            'status': 'success',
            'artist_name': albums[0]['ArtistName'],
            'album_count': len(albums),
            'albums': albums,
            'is_prolific': len(albums) > 5,  # İş kuralı: 5+ albüm = üretken sanatçı
            'popularity_tier': self._calculate_popularity_tier(len(albums))
        }
        
        return profile
    
    def get_playlist_insights(self, playlist_name: str) -> Dict:
        """
        Playlist analizi - İş zekası
        
        Args:
            playlist_name: Playlist adı
            
        Returns:
            Playlist hakkında detaylı bilgi
        """
        result = self.data_service.execute_action(
            'GET_PLAYLIST_DETAILS',
            {'playlist_name': playlist_name}
        )
        
        if result['status'] == 'success' and result['data']:
            data = result['data']
            track_count = data.get('TrackCount', 0)
            
            # İş mantığı: Playlist kategorisi belirle
            category = self._categorize_playlist(track_count)
            
            return {
                'status': 'success',
                'playlist': data,
                'category': category,
                'insights': {
                    'size': 'büyük' if track_count > 50 else 'orta' if track_count > 20 else 'küçük',
                    'estimated_duration_hours': round(track_count * 3.5 / 60, 1),  # Ortalama 3.5 dk/parça
                    'recommended_for': self._get_playlist_recommendation(category)
                }
            }
        
        return result
    
    def get_catalog_overview(self) -> Dict:
        """
        Katalog özeti - İş zekası raporu
        
        Returns:
            Katalog istatistikleri
        """
        # 1. Tüm türleri al
        genres_result = self.data_service.execute_action('LIST_GENRES', {})
        
        # 2. Medya tiplerini al
        media_result = self.data_service.execute_action('LIST_MEDIA_TYPES', {})
        
        if genres_result['status'] == 'success' and media_result['status'] == 'success':
            genres = genres_result['data']
            media_types = media_result['data']
            
            # İş mantığı: Analiz
            popular_genres = [g for g in genres if g['GenreName'] in self.POPULAR_GENRES]
            
            return {
                'status': 'success',
                'summary': {
                    'total_genres': len(genres),
                    'popular_genres': len(popular_genres),
                    'media_formats': len(media_types),
                    'catalog_diversity_score': self._calculate_diversity_score(len(genres))
                },
                'genres': genres,
                'media_types': media_types,
                'popular_genre_list': [g['GenreName'] for g in popular_genres]
            }
        
        return {'status': 'error', 'message': 'Katalog bilgisi alınamadı'}
    
    # ==================== HELPER METHODS (Private) ====================
    
    def _enrich_search_results(self, results: Dict, keyword: str) -> Dict:
        """Arama sonuçlarını zenginleştir"""
        # İş mantığı: Toplam sonuç sayısı
        total_results = sum(
            len(results['data'].get(key, [])) 
            for key in ['tracks', 'albums', 'artists']
        )
        
        results['total_results'] = total_results
        results['search_keyword'] = keyword
        results['has_results'] = total_results > 0
        
        if total_results == 0:
            results['suggestion'] = "Farklı arama terimleri deneyin veya türlere göz atın"
        
        return results
    
    def _categorize_by_price(self, tracks: List[Dict]) -> Dict:
        """Parçaları fiyata göre kategorize et"""
        budget = []      # 0-0.99
        standard = []    # 1.00-1.49
        premium = []     # 1.50+
        
        for track in tracks:
            price = track.get('UnitPrice', 0)
            if price < 1.0:
                budget.append(track)
            elif price < 1.5:
                standard.append(track)
            else:
                premium.append(track)
        
        return {
            'budget': budget,
            'standard': standard,
            'premium': premium,
            'distribution': {
                'budget_count': len(budget),
                'standard_count': len(standard),
                'premium_count': len(premium)
            }
        }
    
    def _calculate_popularity_tier(self, album_count: int) -> str:
        """Sanatçı popülerlik seviyesi"""
        if album_count >= 10:
            return 'legendary'
        elif album_count >= 5:
            return 'established'
        elif album_count >= 2:
            return 'emerging'
        else:
            return 'new'
    
    def _categorize_playlist(self, track_count: int) -> str:
        """Playlist kategorisi"""
        if track_count > 100:
            return 'mega'
        elif track_count > 50:
            return 'comprehensive'
        elif track_count > 20:
            return 'curated'
        else:
            return 'focused'
    
    def _get_playlist_recommendation(self, category: str) -> str:
        """Playlist önerisi"""
        recommendations = {
            'mega': 'Uzun yolculuklar için ideal',
            'comprehensive': 'Gün boyu dinleme için',
            'curated': 'Özel seçkiler için',
            'focused': 'Kısa dinleme seansları için'
        }
        return recommendations.get(category, 'Genel dinleme')
    
    def _calculate_diversity_score(self, genre_count: int) -> str:
        """Katalog çeşitlilik skoru"""
        if genre_count > 20:
            return 'Çok Yüksek'
        elif genre_count > 15:
            return 'Yüksek'
        elif genre_count > 10:
            return 'Orta'
        else:
            return 'Düşük'


class ConversationBusiness:
    """
    Konuşma İş Mantığı
    Oturum yönetimi ve konuşma analizi
    """
    
    # İş kuralları
    MAX_CONVERSATION_TURNS = 50
    INACTIVITY_TIMEOUT_MINUTES = 30
    
    def __init__(self):
        logger.info(f"{LogEmoji.CHECK} ConversationBusiness initialized")
    
    def should_end_session(self, turn_count: int, last_activity: datetime) -> tuple[bool, str]:
        """
        Oturum sonlandırılmalı mı? - İş kuralı
        
        Returns:
            (sonlandır_mı, sebep)
        """
        # İş kuralı 1: Maksimum konuşma sayısı
        if turn_count >= self.MAX_CONVERSATION_TURNS:
            return True, "MAX_TURNS_REACHED"
        
        # İş kuralı 2: İnaktivite timeout
        if datetime.utcnow() - last_activity > timedelta(minutes=self.INACTIVITY_TIMEOUT_MINUTES):
            return True, "INACTIVITY_TIMEOUT"
        
        return False, ""
    
    def calculate_engagement_score(self, turn_count: int, avg_response_length: int) -> Dict:
        """
        Kullanıcı katılım skoru hesapla - İş zekası
        
        Returns:
            Engagement analizi
        """
        # İş mantığı: Skor hesaplama
        turn_score = min(turn_count * 2, 50)  # Max 50 puan
        length_score = min(avg_response_length / 2, 50)  # Max 50 puan
        
        total_score = turn_score + length_score
        
        # Kategori belirleme
        if total_score >= 80:
            category = 'Çok Yüksek'
            insight = 'Kullanıcı çok aktif ve ilgili'
        elif total_score >= 60:
            category = 'Yüksek'
            insight = 'İyi bir etkileşim seviyesi'
        elif total_score >= 40:
            category = 'Orta'
            insight = 'Standart etkileşim'
        else:
            category = 'Düşük'
            insight = 'Daha fazla etkileşim gerekebilir'
        
        return {
            'score': round(total_score, 1),
            'category': category,
            'insight': insight,
            'metrics': {
                'turn_contribution': turn_score,
                'engagement_contribution': length_score
            }
        }
    
    def analyze_sentiment_trend(self, sentiments: List[str]) -> Dict:
        """
        Duygu trendi analizi - İş zekası
        
        Args:
            sentiments: Sentiment listesi (POSITIVE, NEUTRAL, NEGATIVE)
            
        Returns:
            Trend analizi
        """
        if not sentiments:
            return {'trend': 'unknown', 'message': 'Yeterli veri yok'}
        
        # Son 5 sentiment'i al
        recent = sentiments[-5:]
        
        positive_count = recent.count('POSITIVE')
        negative_count = recent.count('NEGATIVE')
        
        # İş mantığı: Trend belirleme
        if positive_count > negative_count:
            trend = 'improving'
            message = 'Müşteri memnuniyeti artıyor'
        elif negative_count > positive_count:
            trend = 'declining'
            message = 'Dikkat: Olumsuz trend'
        else:
            trend = 'stable'
            message = 'Dengeli bir konuşma'
        
        return {
            'trend': trend,
            'message': message,
            'distribution': {
                'positive': sentiments.count('POSITIVE'),
                'neutral': sentiments.count('NEUTRAL'),
                'negative': sentiments.count('NEGATIVE')
            }
        }


class RecommendationBusiness:
    """
    Öneri Sistemi İş Mantığı
    Kişiselleştirilmiş müzik önerileri
    """
    
    def __init__(self, music_business: MusicCatalogBusiness):
        self.music_business = music_business
        logger.info(f"{LogEmoji.CHECK} RecommendationBusiness initialized")
    
    def get_personalized_recommendations(
        self, 
        user_history: List[str],
        preferred_genres: List[str],
        budget: Optional[float] = None
    ) -> Dict:
        """
        Kişiselleştirilmiş öneriler - İş mantığı
        
        Args:
            user_history: Kullanıcının arama geçmişi
            preferred_genres: Tercih edilen türler
            budget: Bütçe (opsiyonel)
            
        Returns:
            Öneriler
        """
        recommendations = []
        
        # İş kuralı: Tercih edilen türlerden öner
        for genre in preferred_genres[:3]:  # En fazla 3 tür
            if budget:
                result = self.music_business.get_budget_friendly_tracks(genre, budget)
            else:
                result = self.music_business.get_recommendations_by_genre(genre)
            
            if result['status'] == 'success':
                recommendations.append({
                    'genre': genre,
                    'tracks': result.get('tracks', result.get('recommendations', {}).get('budget', []))[:3]
                })
        
        return {
            'status': 'success',
            'personalized': True,
            'recommendations': recommendations,
            'based_on': {
                'history_items': len(user_history),
                'preferred_genres': preferred_genres,
                'budget_constraint': budget is not None
            }
        }