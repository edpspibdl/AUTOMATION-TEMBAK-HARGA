import os
import time
import logging
from pywinauto import Application
from dotenv import load_dotenv

logger = logging.getLogger("automation")

# Memuat konfigurasi kredensial dari file .env
load_dotenv()

LOGIN_PERINTAH = os.getenv("LOGIN_PERINTAH", "").strip()
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "").strip()
LOGIN_USER_ID = os.getenv("LOGIN_USER_ID", "").strip()

def login_ho():
    app_path = r"C:\Program Files (x86)\INDOGROSIR\UpdHargaJual\UpdHargaJual.exe"

    if not os.path.exists(app_path):
        logger.error(f"❌ File aplikasi tidak ditemukan di: {app_path}")
        return None

    # Validasi ketersediaan kredensial dari .env
    if not LOGIN_PERINTAH or not LOGIN_PASSWORD or not LOGIN_USER_ID:
        logger.error("❌ Kredensial login belum disetting di file '.env'!")
        logger.error("   Pastikan LOGIN_PERINTAH, LOGIN_PASSWORD, dan LOGIN_USER_ID terisi.")
        return None

    app = None
    try:
        app = Application(backend="uia").connect(path=app_path, timeout=3)
        logger.info("✅ Terhubung ke aplikasi UpdHargaJual yang sudah berjalan.")
    except Exception:
        logger.info("🚀 Membuka aplikasi UpdHargaJual.exe...")
        try:
            app = Application(backend="uia").start(app_path)
        except Exception as e:
            logger.error(f"❌ Gagal menjalankan {app_path}: {e}")
            return None

    try:
        dlg = app.top_window()
        dlg.wait("ready", timeout=30)
        dlg.set_focus()
        time.sleep(1)

        win_text = dlg.window_text().upper()
        # Jika jendela utama 'Update PLU' sudah aktif, berarti sudah login sebelumnya
        if "UPDATE PLU" in win_text:
            logger.info("✅ Sudah berada di jendela utama (Update PLU).")
            return app

        logger.info(f"🔐 Mengisi kredensial login (User: {LOGIN_USER_ID}, Kode: {LOGIN_PERINTAH})...")

        # 1. Coba penargetan elemen secara presisi jika tersedia
        input_success = False
        try:
            txt_perintah = dlg.child_window(auto_id="txtPerintah")
            txt_pass = dlg.child_window(auto_id="txtPass")
            txt_user = dlg.child_window(auto_id="txtUserID")
            btn_login = dlg.child_window(auto_id="BtnLogin")

            if txt_perintah.exists(timeout=1) and txt_pass.exists(timeout=1):
                txt_perintah.set_edit_text(LOGIN_PERINTAH)
                time.sleep(0.2)
                txt_pass.set_edit_text(LOGIN_PASSWORD)
                time.sleep(0.2)
                txt_user.set_edit_text(LOGIN_USER_ID)
                time.sleep(0.2)
                if btn_login.exists(timeout=1):
                    btn_login.click_input()
                else:
                    dlg.type_keys("{ENTER}")
                input_success = True
        except Exception:
            input_success = False

        # 2. Fallback ketikan jika elemen tidak merespons set_edit_text
        if not input_success:
            dlg.type_keys(
                f"{LOGIN_PERINTAH}{{TAB}}"
                f"{LOGIN_PASSWORD}{{TAB}}"
                f"{LOGIN_USER_ID}{{ENTER}}",
                with_spaces=True
            )

        # Tunggu jendela utama 'Update PLU' muncul secara dinamis
        time.sleep(2)
        main_win = app.window(title_re=".*Update PLU.*")
        main_win.wait("ready", timeout=30)
        logger.info("✅ Login berhasil, form Update PLU siap.")
        return app

    except Exception as e:
        logger.error(f"⚠️ Catatan saat proses login: {e}")
        return app
