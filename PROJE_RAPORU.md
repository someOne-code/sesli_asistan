# 🎵 TechFix Müzik Sesli Asistan - Proje Raporu

## Genel Bakış

**TechFix Müzik Sesli Asistan**, müşterilerin sesli komutlarla müzik araması yapabildiği, ürün bilgisi alabildiği ve şirket hakkında bilgi edinebileceği **yapay zeka destekli bir müşteri hizmetleri sistemidir**.

---

## 🏗️ Mimari (Clean Architecture)

```mermaid
graph TB
    subgraph Frontend
        A[index.html - Ana UI]
        B[admin.html - Dashboard]
    end
    
    subgraph API Layer
        C[main.py - FastAPI]
        D[admin_routes.py]
    end
    
    subgraph Services
        E[AssistantService]
    end
    
    subgraph Infrastructure
        F[GroqAIService]
        G[GeminiAIService]
        H[SqliteMusicRepository]
        I[ConversationMemory]
    end
    
    subgraph Database
        J[(hedef.db - SQLite)]
    end
    
    A --> C
    B --> D
    C --> E
    D --> H
    E --> F
    E --> G
    E --> H
    E --> I
    F --> |LLaMA 3.1| K[Groq API]
    G --> |Gemini| L[Google AI]
    H --> J
```

---

## 📁 Dosya Yapısı

| Klasör/Dosya | Açıklama |
|--------------|----------|
| `app/main.py` | FastAPI uygulaması, endpoint'ler |
| `app/core/config.py` | Ayarlar, şirket bilgileri |
| `app/core/interfaces.py` | Soyut arayüzler (DI için) |
| `app/services/assistant_service.py` | İş mantığı katmanı |
| `app/infrastructure/ai/` | AI servisleri (Groq, Gemini) |
| `app/infrastructure/database/` | SQLite repository |
| `app/infrastructure/memory.py` | Redis/In-memory konuşma hafızası |
| `app/routes/admin_routes.py` | Admin API endpoint'leri |
| `index.html` | Ana kullanıcı arayüzü |
| `admin.html` | Admin Dashboard |

---

## ⚙️ Temel Özellikler

### 1. Sesli Asistan
- **Ses Tanıma**: Whisper (Groq API) ile Türkçe ses transkripti
- **Doğal Dil İşleme**: Intent tespiti, duygu analizi
- **Sesli Yanıt**: Edge TTS ile doğal Türkçe ses

### 2. Müzik Veritabanı Entegrasyonu
- Şarkı/albüm/sanatçı arama
- Tür bazlı filtreleme (Rock, Pop, Jazz vb.)
- Fiyat sorguları (en ucuz/pahalı)

### 3. Admin Dashboard
- Görüşme kayıtları tablosu
- İstatistik kartları (toplam çağrı, son 24 saat)
- Otomatik yenileme, responsive tasarım

### 4. Konuşma Hafızası
- Oturum bazlı bağlam koruma
- Redis veya In-Memory desteği

---

## 🔧 Teknoloji Stack

| Kategori | Teknoloji |
|----------|-----------|
| **Backend** | FastAPI, Uvicorn, Python 3.10+ |
| **AI/LLM** | Groq (LLaMA 3.1), Google Gemini |
| **Ses** | Whisper (ASR), Edge-TTS |
| **Veritabanı** | SQLite + SQLAlchemy |
| **Hafıza** | Redis (opsiyonel) |
| **Frontend** | Vanilla HTML/CSS/JS |

---

## 🔄 İş Akışı

```mermaid
sequenceDiagram
    participant U as Kullanıcı
    participant F as Frontend
    participant A as API (FastAPI)
    participant S as AssistantService
    participant AI as AI Service
    participant DB as Database

    U->>F: Ses kaydı
    F->>A: POST /talk (audio)
    A->>AI: Whisper transkripsiyon
    AI-->>A: Metin
    A->>S: process_user_input()
    S->>S: Intent tespiti (keyword)
    alt Müzik Sorgusu
        S->>AI: generate_command()
        AI-->>S: {action, params}
        S->>DB: search_tracks() / get_by_genre()
        DB-->>S: Sonuçlar
    end
    S->>AI: generate_response(context)
    AI-->>S: AI yanıtı
    S-->>A: {ai_response, intent, sentiment}
    A->>A: Edge-TTS → Ses
    A-->>F: Audio stream
    F-->>U: Sesli yanıt
```

---

## 📊 API Endpoint'leri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/` | Ana sayfa (index.html) |
| GET | `/admin` | Admin Dashboard |
| POST | `/talk` | Sesli konuşma |
| POST | `/end-call` | Görüşme özeti |
| GET | `/api/admin/logs` | Görüşme kayıtları |
| GET | `/api/admin/stats` | İstatistikler |

---

## 🚀 Nasıl Çalıştırılır

```bash
# 1. Bağımlılıkları kur
pip install -r requirements.txt

# 2. .env dosyasını ayarla
GROQ_API_KEY=your_key
GEMINI_API_KEY=your_key  # Opsiyonel
AI_PROVIDER=groq  # veya "gemini"

# 3. Uygulamayı başlat
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Erişim:**
- Ana Sayfa: [http://localhost:8000](http://localhost:8000)
- Admin: [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 📈 Gelecek Geliştirmeler (Öneriler)

- [ ] Kullanıcı kimlik doğrulama (Admin Dashboard için)
- [ ] Webhook entegrasyonları (Slack, Discord)
- [ ] Detaylı analitik raporlar
- [ ] Multi-language desteği
- [ ] Mobil uygulama (React Native / Flutter)
