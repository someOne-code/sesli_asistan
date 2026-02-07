# Melody PostgreSQL Şema İncelemesi

Bu doküman, paylaşılan çok kiracılı (multi-tenant) Voice AI SaaS veritabanı şemasına dair kısa teknik değerlendirme notlarını içerir.

## Güçlü Yönler

- **Tenant izolasyonu net:** Hemen tüm tenant-scope tablolarda `tenant_id` var ve RLS aktif.
- **Pratik tip modelleme:** `booking_status`, `call_status`, `industry_type` gibi enum'lar domain'i iyi taşıyor.
- **Performans farkındalığı iyi:** Kritik kolonlarda index ve bazı kompozit indexler düşünülmüş.
- **Fonksiyon yaklaşımı doğru:** `check_availability` ve `create_appointment_from_call` gibi iş kuralları DB tarafında merkezlenmiş.

## Riskler / İyileştirme Önerileri

1. **RLS policy'lerinde `WITH CHECK` eksikliği**
   - Birçok tabloda `FOR ALL USING (...)` var, fakat insert/update için açık `WITH CHECK` tanımlamak daha güvenli olur.
   - Öneri: Her tablo için `SELECT/INSERT/UPDATE/DELETE` politikalarını ayrı yazıp `WITH CHECK` eklemek.

2. **`appointments` çakışma kontrolü**
   - `UNIQUE (tenant_id, start_time)` sadece aynı başlangıç zamanını engeller; örtüşen zaman aralıklarını engellemez.
   - `create_appointment_from_call` içinde `OVERLAPS` kontrolü var ama yarış durumu (race condition) riski sürer.
   - Öneri: `tstzrange(start_time, end_time)` + `EXCLUDE USING gist` constraint ile DB-level garanti.

3. **Timezone tutarlılığı**
   - `check_availability` içinde tenant timezone okunuyor (`v_timezone`) ama slot hesaplama/formatlama tarafında aktif kullanılmıyor.
   - `DATE(start_time) = v_current_date` ifadesi UTC/yerel gün kaymalarında sorun üretebilir.
   - Öneri: Karşılaştırmaları tenant timezone'a göre (`AT TIME ZONE`) standardize etmek.

4. **`availability` modeli tek satır seçiyor**
   - Aynı gün için birden fazla blok (örn. 09:00-12:00 ve 13:00-18:00) desteklenmiyor gibi görünüyor (`LIMIT 1`).
   - Öneri: Günlük çoklu pencere desteği veya normalize edilmiş `availability_windows` tasarımı.

5. **Fonksiyon güvenlik bağlamı**
   - Fonksiyonlar `SECURITY INVOKER` varsayılanıyla çalışır; bu iyi. Ancak Supabase RPC'de hangi role ile çağrıldığı net dokümante edilmeli.
   - Öneri: Gerekirse `SECURITY DEFINER` kullanılacak fonksiyonlarda ownership, `search_path` ve ek guard'lar sıkılaştırılmalı.

6. **Index optimizasyonu fırsatları**
   - `calls(vapi_call_id)` için zaten `UNIQUE` var; ek ayrı index gereksiz olabilir.
   - `appointments` için aktif kayıt sorguları yoğun ise partial index (`WHERE status <> 'CANCELLED'`) faydalı olabilir.

7. **Veri doğrulama katmanı**
   - Telefon ve email için daha sıkı format/check veya normalizasyon (örn. E.164) eklenebilir.
   - `config`, `metadata`, `analysis` JSONB alanları için JSON schema doğrulama yaklaşımı düşünülebilir.

## Hızlı Kazanç (Quick Wins)

- Tüm tenant tablolarında `WITH CHECK` ekle.
- `appointments` için range tabanlı exclusion constraint ekle.
- `check_availability` fonksiyonunda timezone dönüşümünü netleştir.
- `availability` tarafında aynı gün çoklu zaman penceresi desteği aç.

## Sonuç

Şema genel olarak **iyi düşünülmüş ve üretime yakın**. En kritik iki konu: **RLS'de insert/update güvenlik sıkılığı** ve **zaman çakışmasının DB seviyesinde kesin engellenmesi**.
