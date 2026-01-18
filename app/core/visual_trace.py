import datetime
import os

class VisualTrace:
    """
    Sistemin 'Düşünce Sürecini' canlı olarak kaydeden sınıf.
    Kullanıcıya 'sistem şu an ne yapıyor' sorusunun cevabını verir.
    """
    LOG_FILE = "CANLI_TAKIP_LOGU.md"
    
    @staticmethod
    def clear():
        """Her yeni başlatmada log dosyasını temizler."""
        with open(VisualTrace.LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"# 🕵️‍♂️ CANLI SİSTEM TAKİBİ\n")
            f.write(f"Başlatılma Zamanı: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write("Bu dosya, sesli asistanın arka plandaki tüm kararlarını anlık gösterir.\n")
            f.write("----------------------------------------------------------------------\n\n")

    @staticmethod
    def _write(content):
        mode = "a" if os.path.exists(VisualTrace.LOG_FILE) else "w"
        try:
            with open(VisualTrace.LOG_FILE, mode, encoding="utf-8") as f:
                f.write(content + "\n")
        except Exception as e:
            print(f"Loglama Hatası: {e}")

    @staticmethod
    def start_request(tenant_id, user_text):
        VisualTrace._write(f"\n## 🚀 [{datetime.datetime.now().strftime('%H:%M:%S')}] YENİ İSTEK GELDİ")
        VisualTrace._write(f"- **Kiracı (Tenant):** `{tenant_id}`")
        VisualTrace._write(f"- **Duyulan Ses:** \"{user_text}\"")
        VisualTrace._write("")

    @staticmethod
    def log_step(component, action, value=None):
        icon_map = {
            "Normalizer": "🧹",
            "Gate": "🛡️",
            "Intent": "🧠",
            "Database": "🗄️",
            "AI": "🤖",
            "Prompt": "📝",
            "Error": "💥"
        }
        icon = icon_map.get(component, "⚙️")
        
        msg = f"### {icon} {component}: {action}"
        VisualTrace._write(msg)
        if value:
            VisualTrace._write(f"> `{value}`")
        VisualTrace._write("")

    @staticmethod
    def log_prompt_snapshot(prompt):
        VisualTrace._write("### 📝 AI'ya Gönderilen 'Kişilik' (System Prompt)")
        VisualTrace._write("```text")
        # İlk 5 satırı al, gerisini özetle
        lines = prompt.split('\n')
        preview = '\n'.join(lines)  # Hepsini basalım ki hatayı gör
        VisualTrace._write(preview)
        VisualTrace._write("```")
        
        # OTOMATİK HATA TESPİTİ
        if "Chinook" in prompt and "Berber" not in prompt:
             VisualTrace._write("\n⚠️ **DİKKAT:** Prompt içinde 'Chinook' kelimesi tespit edildi ama 'Berber' yok!")
             VisualTrace._write("👉 **Teşhis:** Asistan kendini Müzik Mağazası (Chinook) sanıyor olabilir.")
        elif "Berber" in prompt:
             VisualTrace._write("\n✅ **ONAY:** Prompt içinde 'Berber' kimliği görüldü.")
        
        VisualTrace._write("\n---\n")

    @staticmethod
    def log_db_result(query, count, items=None):
        VisualTrace._write(f"### 🗄️ Veritabanı Sonucu")
        VisualTrace._write(f"- **Sorgu:** `{query}`")
        VisualTrace._write(f"- **Bulunan Kayıt:** {count}")
        if items:
            VisualTrace._write(f"- **Detaylar:** {items}")
        VisualTrace._write("")
