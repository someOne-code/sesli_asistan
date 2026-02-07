# Melody Schema - Task-by-Task İmplementation Planı

Bu plan, `SCHEMA_FEEDBACK.md` içindeki önerileri **uygulanabilir, sıraya alınmış görevler** haline getirir.

## Uygulama Sırası (Önerilen)

1. RLS hardening (`WITH CHECK`)
2. Appointment conflict'i DB seviyesinde kesin engelleme
3. Timezone standardizasyonu
4. Availability modelinin çoklu zaman penceresine çıkarılması
5. Function security/RPC çağrı modelinin netleştirilmesi
6. Index sadeleştirme + hedefli index ekleme
7. Veri doğrulama (E.164 + JSON schema benzeri guard)

---

## TASK 1 — RLS Hardening: `WITH CHECK` ve policy ayrıştırma

### Hedef
Tenant tablolarında `FOR ALL USING` yerine `SELECT/INSERT/UPDATE/DELETE` politikalarını açıkça ayırıp `INSERT/UPDATE` için `WITH CHECK` uygulamak.

### Kapsam Tablolar
- `customers`
- `services`
- `schedules`
- `availability`
- `appointments`
- `calls`
- `knowledge_base`

### Yapılacaklar
1. Mevcut policy'leri drop et.
2. Her tablo için 4 policy ekle:
   - `SELECT ... USING (...)`
   - `INSERT ... WITH CHECK (...)`
   - `UPDATE ... USING (...) WITH CHECK (...)`
   - `DELETE ... USING (...)`
3. Staging ortamında tenant-tenant arası negatif testleri çalıştır.

### Kabul Kriteri
- Tenant A, Tenant B kaydını `INSERT/UPDATE/DELETE/SELECT` ile manipüle edemez.
- Uygulama mevcut akışlarında 403/permission regressions oluşmaz.

### SQL İskeleti (örnek: `customers`)
```sql
DROP POLICY IF EXISTS "Tenants can manage own customers" ON customers;

CREATE POLICY customers_select_own
ON customers FOR SELECT
USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

CREATE POLICY customers_insert_own
ON customers FOR INSERT
WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

CREATE POLICY customers_update_own
ON customers FOR UPDATE
USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()))
WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

CREATE POLICY customers_delete_own
ON customers FOR DELETE
USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
```

---

## TASK 2 — Appointment çakışmalarını DB seviyesinde garanti altına alma

### Hedef
Race condition dahil olmak üzere çakışan randevuları DB constraint ile kesin engellemek.

### Yapılacaklar
1. `btree_gist` extension'ı aktif et.
2. `appointments` üzerinde `tstzrange(start_time, end_time, '[)')` temelli exclusion constraint ekle.
3. `status = 'CANCELLED'` kayıtlarını hariç tutacak partial exclusion yaklaşımı uygula.
4. Uygulama tarafında constraint violation'ı domain hatasına map et.

### Kabul Kriteri
- Aynı tenant içinde overlap eden iki aktif appointment aynı anda insert edilemez.
- Farklı tenant'ların aynı saat aralığı birbirini etkilemez.
- `CANCELLED` kayıtlar yeni booking'i bloklamaz.

### SQL İskeleti
```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE appointments
DROP CONSTRAINT IF EXISTS unique_tenant_timeslot;

ALTER TABLE appointments
ADD CONSTRAINT appointments_no_overlap
EXCLUDE USING gist (
  tenant_id WITH =,
  tstzrange(start_time, end_time, '[)') WITH &&
)
WHERE (status <> 'CANCELLED');
```

---

## TASK 3 — `check_availability` timezone standardizasyonu

### Hedef
Tarih/gün hesaplarının tenant timezone'a göre deterministik çalışması.

### Yapılacaklar
1. `DATE(start_time) = v_current_date` filtresini timezone-aware hale getir.
2. Slot oluştururken `v_timezone` ile normalize et.
3. Fonksiyon çıktısında hem ISO timestamp hem local saat alanı dönmeyi değerlendir.

### Kabul Kriteri
- UTC gün değişimlerinde slot kayması oluşmaz.
- `Europe/Istanbul` gibi timezone'larda beklenen gün/saat döner.

### SQL Refactor İpucu
```sql
-- örnek filtre mantığı
(start_time AT TIME ZONE v_timezone)::date = v_current_date
```

---

## TASK 4 — Availability modelini çoklu pencereye çıkarma

### Hedef
Aynı gün birden fazla çalışma aralığı (örn. sabah+öğleden sonra) desteklemek.

### Yapılacaklar
1. `availability` sorgusundaki `LIMIT 1` yaklaşımını kaldır.
2. İki opsiyondan birini seç:
   - (A) mevcut tabloyu çok satırlı kullanım için bırak, fonksiyonda hepsini işle
   - (B) `availability_windows` adında normalize yeni tablo ekle
3. `check_availability` içinde gün içi pencereleri sırayla işleyip slotları birleştir.

### Kabul Kriteri
- Aynı gün 2+ time window doğru slot üretir.
- Date override kuralı (özel gün) weekly kuralı override eder.

---

## TASK 5 — Function security ve Supabase RPC çağrı modelini sertleştirme

### Hedef
Fonksiyonların hangi role ile çalıştığı ve erişim sınırlarının net tanımlanması.

### Yapılacaklar
1. `SECURITY INVOKER` varsayılanının korunduğunu doğrula.
2. RPC için `GRANT EXECUTE` yetkilerini rol bazlı netleştir (`anon`, `authenticated`, `service_role`).
3. Gerekli fonksiyonlarda `SET search_path` ile güvenli path sabitle.
4. Dokümantasyona role matrix ekle.

### Kabul Kriteri
- Yetkisiz role fonksiyon çalıştıramaz.
- Fonksiyonlar beklenmeyen şema/path etkisi yaşamaz.

---

## TASK 6 — Index optimizasyonu (sadeleştirme + hedefli ekleme)

### Hedef
Gereksiz index yükünü azaltıp okuma/yazma dengesini iyileştirmek.

### Yapılacaklar
1. `calls(vapi_call_id)` için redundant index'i kaldır (UNIQUE zaten index üretir).
2. Yoğun sorgular için partial index değerlendir:
   - `appointments` aktif kayıtlar: `WHERE status <> 'CANCELLED'`
3. `EXPLAIN (ANALYZE, BUFFERS)` ile öncesi/sonrası karşılaştır.

### Kabul Kriteri
- Kritik sorgu latency'sinde ölçülebilir iyileşme.
- Insert/Update performansı olumsuz etkilenmez.

---

## TASK 7 — Veri doğrulama katmanı

### Hedef
Telefon/email/JSON alanlarında veri kalitesini artırmak.

### Yapılacaklar
1. Telefonu E.164 normalizasyon pipeline'ına al (`+90555...`).
2. Gerekli tablolarda check constraint veya trigger ile format doğrula.
3. JSONB kolonları için minimum key/shape kontrolü yapan SQL fonksiyonları ekle.

### Kabul Kriteri
- Geçersiz formatlar DB katmanında reddedilir.
- Geçerli veriler mevcut akışları bozmaz.

---

## Önerilen Sprint Planı

### Sprint 1 (yüksek risk / hızlı kazanım)
- TASK 1 (RLS hardening)
- TASK 2 (Exclusion constraint)

### Sprint 2 (doğruluk)
- TASK 3 (Timezone)
- TASK 4 (Çoklu availability penceresi)

### Sprint 3 (operasyonel olgunluk)
- TASK 5 (Function security)
- TASK 6 (Index tuning)
- TASK 7 (Validation)

---

## Test Matriksi (özet)

- **Security Tests**: cross-tenant CRUD denial
- **Concurrency Tests**: aynı slot için paralel booking denemesi
- **Timezone Tests**: UTC boundary + tenant local day
- **Availability Tests**: tek pencere / çok pencere / override date
- **Performance Tests**: p95 latency (`check_availability`, appointment insert)

---

## Çıktı Beklentisi (Deliverables)

1. SQL migration dosyaları (task bazlı, rollback notlarıyla)
2. RPC/role yetki dokümantasyonu
3. Test raporu (security + concurrency + latency)
4. Güncel ERD / şema notları

