"""
Conversation Logger - Görüşme notlarını TXT dosyasına kaydet
"""

import os
from datetime import datetime
from typing import Optional
from config import logger, LogEmoji


class ConversationLogger:
    """
    Görüşmeleri TXT dosyasına kaydeden sınıf
    """
    
    def __init__(self, log_directory: str = "conversation_logs"):
        """
        Args:
            log_directory: Görüşme notlarının kaydedileceği klasör
        """
        self.log_directory = log_directory
        
        # Klasörü oluştur (yoksa)
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)
            logger.info(f"{LogEmoji.CHECK} Conversation logs directory created: {log_directory}")
    
    def save_conversation(
        self,
        session_id: str,
        customer_text: str,
        ai_response: str,
        sentiment: str,
        intent: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Tek bir görüşme turunu kaydet
        
        Args:
            session_id: Oturum ID'si
            customer_text: Müşteri mesajı
            ai_response: AI yanıtı
            sentiment: Duygu (POSITIVE, NEUTRAL, NEGATIVE)
            intent: Niyet (MUSIC_QUERY, CHAT, vb.)
            timestamp: Zaman damgası (opsiyonel)
        
        Returns:
            Dosya yolu
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Dosya adı: session_id_YYYYMMDD.txt
        date_str = timestamp.strftime("%Y%m%d")
        filename = f"{session_id}_{date_str}.txt"
        filepath = os.path.join(self.log_directory, filename)
        
        # Görüşme notu formatı
        log_entry = f"""
{'='*70}
Tarih/Saat: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
Oturum ID: {session_id}
Niyet: {intent}
Duygu: {sentiment}
{'='*70}

MÜŞTERİ:
{customer_text}

AI YANITI:
{ai_response}

{'='*70}

"""
        
        # Dosyaya ekle (append mode)
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.info(f"{LogEmoji.WRITE} Conversation logged to: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Failed to save conversation to file: {e}")
            return ""
    
    def save_session_summary(
        self,
        session_id: str,
        summary: str,
        total_turns: int,
        engagement_score: Optional[dict] = None
    ) -> str:
        """
        Oturum özeti kaydet
        
        Args:
            session_id: Oturum ID'si
            summary: AI tarafından üretilen özet
            total_turns: Toplam konuşma turu
            engagement_score: Katılım skoru (opsiyonel)
        
        Returns:
            Dosya yolu
        """
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y%m%d")
        filename = f"{session_id}_{date_str}.txt"
        filepath = os.path.join(self.log_directory, filename)
        
        # Özet formatı
        summary_text = f"""
{'#'*70}
OTURUM ÖZETİ
{'#'*70}
Tarih/Saat: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
Oturum ID: {session_id}
Toplam Konuşma: {total_turns} tur
"""
        
        # Engagement score varsa ekle
        if engagement_score:
            summary_text += f"""
Katılım Skoru: {engagement_score.get('score', 'N/A')}
Kategori: {engagement_score.get('category', 'N/A')}
"""
        
        summary_text += f"""
{'#'*70}

ÖZET:
{summary}

{'#'*70}

"""
        
        # Dosyaya ekle
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(summary_text)
            
            logger.info(f"{LogEmoji.CHECK} Session summary saved to: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Failed to save summary to file: {e}")
            return ""
    
    def get_session_log_path(self, session_id: str, date: Optional[datetime] = None) -> str:
        """
        Bir oturumun log dosya yolunu döndür
        
        Args:
            session_id: Oturum ID'si
            date: Tarih (opsiyonel, bugün varsayılan)
        
        Returns:
            Dosya yolu
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y%m%d")
        filename = f"{session_id}_{date_str}.txt"
        return os.path.join(self.log_directory, filename)
    
    def read_session_log(self, session_id: str, date: Optional[datetime] = None) -> str:
        """
        Bir oturumun log dosyasını oku
        
        Args:
            session_id: Oturum ID'si
            date: Tarih (opsiyonel)
        
        Returns:
            Dosya içeriği (yoksa boş string)
        """
        filepath = self.get_session_log_path(session_id, date)
        
        if not os.path.exists(filepath):
            logger.warning(f"{LogEmoji.WARNING} Log file not found: {filepath}")
            return ""
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Failed to read log file: {e}")
            return ""
    
    def list_session_logs(self, session_id: Optional[str] = None) -> list:
        """
        Tüm log dosyalarını listele
        
        Args:
            session_id: Belirli bir oturum (opsiyonel, None ise tümü)
        
        Returns:
            Log dosyası listesi
        """
        try:
            all_files = os.listdir(self.log_directory)
            txt_files = [f for f in all_files if f.endswith('.txt')]
            
            if session_id:
                # Belirli bir oturum için filtrele
                txt_files = [f for f in txt_files if f.startswith(session_id)]
            
            return sorted(txt_files, reverse=True)  # En yeni önce
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Failed to list log files: {e}")
            return []
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        Eski log dosyalarını temizle
        
        Args:
            days_to_keep: Kaç günlük log saklanacak
        
        Returns:
            Silinen dosya sayısı
        """
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for filename in os.listdir(self.log_directory):
                filepath = os.path.join(self.log_directory, filename)
                
                # Dosya yaşını kontrol et
                if os.path.getmtime(filepath) < cutoff_date:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"{LogEmoji.TRASH} Deleted old log: {filename}")
            
            if deleted_count > 0:
                logger.info(f"{LogEmoji.CHECK} Cleaned up {deleted_count} old log files")
            
            return deleted_count
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Failed to cleanup logs: {e}")
            return 0
    
    def export_session_to_markdown(self, session_id: str, date: Optional[datetime] = None) -> str:
        """
        Oturum logunu Markdown formatına çevir
        
        Args:
            session_id: Oturum ID'si
            date: Tarih (opsiyonel)
        
        Returns:
            Markdown dosya yolu
        """
        content = self.read_session_log(session_id, date)
        
        if not content:
            return ""
        
        # Markdown formatına çevir
        md_content = f"""# Görüşme Kaydı
**Oturum ID:** {session_id}
**Tarih:** {date.strftime("%Y-%m-%d") if date else datetime.now().strftime("%Y-%m-%d")}

---

{content}
"""
        
        # Markdown dosyasına kaydet
        md_filepath = self.get_session_log_path(session_id, date).replace('.txt', '.md')
        
        try:
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"{LogEmoji.CHECK} Markdown export created: {md_filepath}")
            return md_filepath
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Failed to export to Markdown: {e}")
            return ""


# Global instance
conversation_logger = ConversationLogger()