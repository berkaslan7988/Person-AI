"""Person AI — Internationalisation (TR / EN)."""

STRINGS = {
    "app_title": {"tr": "Person AI", "en": "Person AI"},
    "splash_subtitle": {"tr": "AI Karakter Sohbeti", "en": "AI Character Chat"},
    "init_error": {"tr": "Başlatma hatası:", "en": "Startup error:"},
    "tab_chat": {"tr": "Sohbet", "en": "Chat"},
    "tab_settings": {"tr": "Ayarlar", "en": "Settings"},
    "tab_characters": {"tr": "Karakterler", "en": "Characters"},

    # ── Onboarding ────────────────────────────────────────────
    "ob1_title": {"tr": "Hoş Geldiniz!", "en": "Welcome!"},
    "ob1_desc": {"tr": "Person AI ile yapay zeka karakterlerle doğal sohbetler yapın.\nKişiliklerini siz belirleyin!", "en": "Have natural conversations with AI characters in Person AI.\nYou define their personalities!"},
    "ob2_title": {"tr": "Karakter Galerisi", "en": "Character Gallery"},
    "ob2_desc": {"tr": "Kendi karakterlerinizi oluşturun, SillyTavern V2 kartlarını içe aktarın,\nveya AI ile avatar üretin.", "en": "Create your own characters, import SillyTavern V2 cards,\nor generate avatars with AI."},
    "ob3_title": {"tr": "Hazırsınız!", "en": "You're Ready!"},
    "ob3_desc": {"tr": "Ayarlardan model seçin, kişiliği düzenleyin ve sohbete başlayın.", "en": "Pick a model in Settings, tune the personality and start chatting."},
    "ob_skip": {"tr": "Atla", "en": "Skip"},
    "ob_next": {"tr": "Sonraki →", "en": "Next →"},
    "ob_start": {"tr": "Başla ✨", "en": "Start ✨"},

    # ── Settings: section tabs ────────────────────────────────
    "sec_model": {"tr": "Model", "en": "Model"},
    "sec_character": {"tr": "Karakter", "en": "Character"},
    "sec_appearance": {"tr": "Görünüm", "en": "Appearance"},
    "sec_data": {"tr": "Veri", "en": "Data"},
    "sec_advanced": {"tr": "Gelişmiş", "en": "Advanced"},

    # ── Settings: model ───────────────────────────────────────
    "model_section": {"tr": "AI Model Seçimi", "en": "AI Model Selection"},
    "api_keys": {"tr": "API Anahtarları", "en": "API Keys"},
    "keys_saved_info": {"tr": "Kaydedilen anahtarlar şifrelenmiş olarak saklanır.", "en": "Saved keys are stored obfuscated."},
    "save_key_tooltip": {"tr": "API anahtarını kaydet", "en": "Save API key"},
    "api_key_saved": {"tr": "API anahtarı kaydedildi!", "en": "API key saved!"},
    "api_keys_missing": {"tr": "API anahtarı eksik!", "en": "API Keys Missing!"},

    # ── Settings: character ───────────────────────────────────
    "character_section": {"tr": "Hızlı Karakter Ayarları", "en": "Quick Character Settings"},
    "character_detail_hint": {"tr": "Detaylı düzenleme için Karakterler sekmesini kullanın.", "en": "Use the Characters tab for detailed editing."},
    "field_personality": {"tr": "Kişilik", "en": "Personality"},
    "avatar_url_hint": {"tr": "https://... (karakter fotoğrafı)", "en": "https://... (character photo)"},

    # ── Settings: appearance ──────────────────────────────────
    "appearance_section": {"tr": "Görünüm", "en": "Appearance"},
    "theme": {"tr": "Tema", "en": "Theme"},
    "theme_mode": {"tr": "Tema Modu", "en": "Theme Mode"},
    "dark": {"tr": "Karanlık", "en": "Dark"},
    "light": {"tr": "Aydınlık", "en": "Light"},
    "system": {"tr": "Sistem", "en": "System"},
    "accent": {"tr": "Aksan Rengi", "en": "Accent Color"},
    "accent_default": {"tr": "Varsayılan", "en": "Default"},
    "language": {"tr": "Dil", "en": "Language"},
    "tr": {"tr": "Türkçe", "en": "Turkish"},
    "en": {"tr": "English", "en": "English"},
    "chat_bg_section": {"tr": "Sohbet Arka Planı", "en": "Chat Background"},
    "chat_bg_desc": {"tr": "Sohbet ekranı için bir arka plan görseli URL'i girin.", "en": "Enter a background image URL for the chat screen."},
    "chat_bg_label": {"tr": "Sohbet Arka Plan URL'i", "en": "Chat Background URL"},
    "chat_bg_hint": {"tr": "https://... (boş bırakılırsa düz renk)", "en": "https://... (plain color if empty)"},
    "user_profile_section": {"tr": "Kullanıcı Profili", "en": "User Profile"},
    "user_profile_desc": {"tr": "Kendi adınızı ve avatar fotoğrafınızı ayarlayın. Yeni mesajlarda görünür.", "en": "Set your own name and avatar photo. Shown on new messages."},
    "user_name_label": {"tr": "Kullanıcı Adı (opsiyonel)", "en": "User Name (optional)"},
    "user_name_hint": {"tr": "Boş bırakılırsa 'Sen' olarak görünür", "en": "Shown as 'You' if left empty"},
    "user_avatar_label": {"tr": "Kullanıcı Avatar URL'i (opsiyonel)", "en": "User Avatar URL (optional)"},
    "user_avatar_hint": {"tr": "https://... (profil fotoğrafı)", "en": "https://... (profile photo)"},
    "user_persona_label": {"tr": "Kişiliğin / İsteklerin (opsiyonel)", "en": "Your Persona / Requests (optional)"},
    "user_persona_desc": {"tr": "İsteğe bağlı: Kendinizi tanıtın. Doldurursanız yapay zeka sizi tanır ve buna göre davranır.", "en": "Optional: introduce yourself. If filled, the AI will know you and adapt."},
    "user_persona_hint": {"tr": "Örn: Adım Mert, 25 yaşındayım, bana samimi ve esprili davran...", "en": "E.g.: My name is Mert, I'm 25, be friendly and witty with me..."},

    # ── Settings: data ────────────────────────────────────────
    "data_section": {"tr": "Veri Yönetimi", "en": "Data Management"},
    "export_all": {"tr": "Tüm Veriyi JSON Dışa Aktar", "en": "Export All Data as JSON"},
    "saved_characters": {"tr": "Kayıtlı Karakterler", "en": "Saved Characters"},
    "no_data": {"tr": "Henüz veri yok.", "en": "No data yet."},
    "reset_all": {"tr": "⚠ Tüm Verileri Sıfırla", "en": "⚠ Reset All Data"},
    "reset_confirm_title": {"tr": "Tüm verileri sıfırla?", "en": "Reset all data?"},
    "reset_confirm_body": {"tr": "Tüm karakterler, sohbetler ve veriler KALICI olarak silinecek. Bu işlem geri alınamaz!", "en": "All characters, chats and data will be PERMANENTLY deleted. This cannot be undone!"},
    "reset_btn": {"tr": "SIFIRLA", "en": "RESET"},
    "all_reset_done": {"tr": "Tüm veriler sıfırlandı.", "en": "All data has been reset."},

    # ── Settings: advanced ────────────────────────────────────
    "advanced_section": {"tr": "Model Parametreleri", "en": "Model Parameters"},
    "temperature_label": {"tr": "Sıcaklık (Temperature)", "en": "Temperature"},
    "top_p_label": {"tr": "Top-P", "en": "Top-P"},
    "fp_label": {"tr": "Sıklık Cezası", "en": "Frequency Penalty"},
    "max_tokens_label": {"tr": "Max Token", "en": "Max Tokens"},
    "context_label": {"tr": "Bağlam (Mesaj Sayısı)", "en": "Context (Message Count)"},
    "apply_all": {"tr": "✓ Tüm Ayarları Uygula", "en": "✓ Apply All Settings"},
    "settings_applied": {"tr": "✓ Tüm ayarlar uygulandı!", "en": "✓ All settings applied!"},

    # ── Chat ──────────────────────────────────────────────────
    "type_message": {"tr": "Mesaj yaz...", "en": "Type a message..."},
    "send": {"tr": "Gönder", "en": "Send"},
    "scroll_down": {"tr": "En alta git", "en": "Scroll to bottom"},
    "search_placeholder": {"tr": "Mesajlarda ara...", "en": "Search messages..."},
    "search_tab": {"tr": "Ara", "en": "Search"},
    "history_tab": {"tr": "Geçmiş", "en": "History"},
    "no_results": {"tr": "Sonuç bulunamadı.", "en": "No results found."},
    "no_sessions": {"tr": "Kayıtlı sohbet yok.", "en": "No saved chats."},
    "session_loaded": {"tr": "Sohbet yüklendi.", "en": "Chat loaded."},
    "messages_count": {"tr": "mesaj", "en": "messages"},
    "sessions_count": {"tr": "sohbet", "en": "chats"},
    "model_limit": {"tr": "Limit aşıldı →", "en": "Rate limited →"},
    "all_models_failed": {"tr": "Tüm modeller başarısız. Lütfen bekleyin.", "en": "All models failed. Please wait."},
    "error_prefix": {"tr": "Hata:", "en": "Error:"},
    "no_key_hint": {"tr": "API anahtarı gerekli — Ayarlar sekmesine gidin", "en": "API key required — go to the Settings tab"},
    "add_key_first": {"tr": "Önce Ayarlar → API Anahtarları bölümünden bir anahtar ekleyin.", "en": "First add a key in Settings → API Keys."},
    "clear_chat_tooltip": {"tr": "Sohbeti temizle", "en": "Clear chat"},
    "clear_chat_title": {"tr": "Sohbeti temizle?", "en": "Clear chat?"},
    "clear_chat_body": {"tr": "Tüm mesajlar silinecek. Bu işlem geri alınamaz.", "en": "All messages will be deleted. This cannot be undone."},
    "btn_clear": {"tr": "Temizle", "en": "Clear"},
    "chat_cleared": {"tr": "Sohbet temizlendi.", "en": "Chat cleared."},
    "editing_message": {"tr": "Mesaj düzenleniyor", "en": "Editing message"},
    "copied": {"tr": "Kopyalandı", "en": "Copied"},
    "copy_failed": {"tr": "Kopyalanamadı", "en": "Copy failed"},
    "tooltip_copy": {"tr": "Kopyala", "en": "Copy"},
    "tooltip_regen": {"tr": "Yeniden oluştur", "en": "Regenerate"},
    "tooltip_edit": {"tr": "Düzenle", "en": "Edit"},
    "tooltip_delete": {"tr": "Sil", "en": "Delete"},

    # ── Gallery ───────────────────────────────────────────────
    "new_character": {"tr": "+ Yeni Karakter", "en": "+ New Character"},
    "no_characters": {"tr": "Henüz kayıtlı karakter yok.\n'+ Yeni Karakter' butonuyla ekleyin.", "en": "No characters saved yet.\nUse '+ New Character' to add one."},
    "new_chat_tooltip": {"tr": "Yeni sohbet başlat", "en": "Start new chat"},
    "new_chat": {"tr": "Yeni sohbet", "en": "New chat"},
    "empty_chat": {"tr": "Boş sohbet", "en": "Empty chat"},
    "char_selected": {"tr": "seçildi!", "en": "selected!"},
    "chat_started": {"tr": "ile sohbet başlatıldı!", "en": "chat started!"},
    "new_chat_with": {"tr": "ile yeni sohbet!", "en": "new chat started!"},
    "deleted_simple": {"tr": "silindi.", "en": "deleted."},
    "irreversible": {"tr": "Bu işlem geri alınamaz.", "en": "This cannot be undone."},

    # ── Character form ────────────────────────────────────────
    "form_title_create": {"tr": "Yeni Karakter", "en": "New Character"},
    "form_title_edit": {"tr": "Karakteri Düzenle", "en": "Edit Character"},
    "field_name": {"tr": "Karakter Adı", "en": "Character Name"},
    "field_traits": {"tr": "Kişilik & Hikaye", "en": "Personality & Backstory"},
    "field_greeting": {"tr": "Greeting (ilk mesaj)", "en": "Greeting (first message)"},
    "field_examples": {"tr": "Örnek Diyaloglar (her satır bir örnek)", "en": "Example Dialogues (one per line)"},
    "field_tags": {"tr": "Etiketler (virgülle ayır)", "en": "Tags (comma separated)"},
    "field_avatar": {"tr": "Avatar URL", "en": "Avatar URL"},
    "field_avatar_label": {"tr": "Avatar", "en": "Avatar"},
    "btn_pick_file": {"tr": "Dosyadan seç", "en": "Pick file"},
    "btn_import_v2": {"tr": "ST V2 Kartı İçe Aktar", "en": "Import ST V2 Card"},
    "btn_cancel": {"tr": "İptal", "en": "Cancel"},
    "btn_save": {"tr": "Kaydet", "en": "Save"},
    "btn_delete": {"tr": "Sil", "en": "Delete"},
    "btn_close": {"tr": "Kapat", "en": "Close"},
    "char_saved": {"tr": "kaydedildi!", "en": "saved!"},
    "char_deleted": {"tr": "ve tüm sohbetleri silindi.", "en": "and all chats deleted."},
    "char_imported": {"tr": "içe aktarıldı!", "en": "imported!"},
    "import_error": {"tr": "İçe aktarma hatası:", "en": "Import error:"},
    "invalid_format": {"tr": "Geçersiz dosya formatı (.json veya .png bekleniyor)", "en": "Invalid file format (.json or .png expected)"},
    "png_no_meta": {"tr": "PNG'den metadata çıkarılamadı. Aynı klasörde aynı isimli .json dosyası bulunmalı.", "en": "Could not extract metadata from PNG. A .json file with the same name should exist."},
    "export_ok": {"tr": "Dışa aktarıldı:", "en": "Exported:"},
    "delete_confirm_title": {"tr": "silinsin mi?", "en": "delete?"},
    "delete_confirm_body": {"tr": "Karakter ve tüm sohbetleri kalıcı olarak silinecek.", "en": "Character and all chats will be permanently deleted."},

    # ── Character detail ──────────────────────────────────────
    "tab_edit": {"tr": "Düzenle", "en": "Edit"},
    "tab_sessions": {"tr": "Sohbetler", "en": "Chats"},
    "continue_chat": {"tr": "Devam et", "en": "Continue"},
    "delete_session_title": {"tr": "Sohbet silinsin mi?", "en": "Delete chat?"},
    "btn_new_chat": {"tr": "+ Yeni Sohbet", "en": "+ New Chat"},
    "tags_label": {"tr": "Etiketler", "en": "Tags"},
    "tags_hint": {"tr": "arkadaş, anime, ...", "en": "friend, anime, ..."},

    # ── Provider errors (user-facing) ─────────────────────────
    "err_unknown": {"tr": "Bilinmeyen bir hata oluştu.", "en": "An unknown error occurred."},
    "err_timeout": {"tr": "Sunucu yanıt vermedi (zaman aşımı). Lütfen tekrar deneyin.", "en": "The server did not respond (timeout). Please try again."},
    "err_connection": {"tr": "İnternet bağlantısı veya sunucuya erişim hatası.", "en": "Internet connection or server access error."},
    "err_auth": {"tr": "API anahtarı geçersiz veya eksik.", "en": "API key is invalid or missing."},
    "err_rate_limit": {"tr": "İstek limiti aşıldı. Lütfen biraz bekleyin.", "en": "Rate limit exceeded. Please wait a bit."},
    "err_content_filter": {"tr": "İçerik filtresi yanıtı engelledi.", "en": "The content filter blocked the response."},
    "err_bad_response": {"tr": "Sunucudan geçersiz yanıt alındı.", "en": "Invalid response received from the server."},

    # ── Model badges ──────────────────────────────────────────
    "badge_fast": {"tr": "⚡ Hızlı", "en": "⚡ Fast"},
    "badge_smart": {"tr": "🧠 Akıllı", "en": "🧠 Smart"},
    "badge_free": {"tr": "🆓 Ücretsiz", "en": "🆓 Free"},

    # ── Misc ──────────────────────────────────────────────────
    "greeting_default": {"tr": "Merhaba, ben", "en": "Hello, I'm"},
    "greeting_start": {"tr": "Sohbet etmeye başlayalım!", "en": "Let's start chatting!"},

    # AI Avatar Generation
    "generate_avatar": {"tr": "🤖 AI ile Avatar Üret", "en": "🤖 Generate Avatar with AI"},
    "generating_avatar": {"tr": "Avatar üretiliyor...", "en": "Generating avatar..."},
    "avatar_generated": {"tr": "Avatar üretildi!", "en": "Avatar generated!"},
    "avatar_prompt_hint": {"tr": "Karakter açıklamasından avatar üretmek için tıkla", "en": "Click to generate avatar from description"},
}


from .ui.app_state import state as _state


def t(key: str, **kwargs) -> str:
    """Return the translated string for the current language.

    Optional keyword arguments are interpolated with str.format().
    """
    lang = getattr(_state, "language", "tr")
    entry = STRINGS.get(key, {})
    text = entry.get(lang, entry.get("en", key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
