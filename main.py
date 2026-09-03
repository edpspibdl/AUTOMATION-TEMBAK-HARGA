import sys
import os
import ctypes
import time
import logging
from src.login import login_ho
from src.update_harga import update_harga
from src.aplikasi_kedua import jalankan_semua_tahap_indogrosir

def setup_logger():
    """Inisialisasi logger agar mencatat ke console dan file log/run.log."""
    os.makedirs("log", exist_ok=True)
    logger = logging.getLogger("automation")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # File Handler
    fh = logging.FileHandler("log/run.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fh_fmt)
    logger.addHandler(fh)

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    ch.setFormatter(ch_fmt)
    logger.addHandler(ch)

    return logger

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def main():
    logger = setup_logger()
    print("="*60)
    logger.info("=== START AUTOMATION SYSTEM INDOGROSIR ===")
    print("="*60)
    
    try:
        # TAHAP 1: Login HO & Update Harga
        logger.info("[1/2] Menjalankan Tahap 1 (Login & Input Harga)...")
        app = login_ho()
        if app:
            update_harga(app)
        else:
            logger.error("❌ Login gagal atau aplikasi tidak dapat dibuka. Otomasi dihentikan.")
            return

        time.sleep(5)

        # TAHAP 2 & 3: Aplikasi Indogrosir Setup Update Harga
        logger.info("[2/2] Menjalankan Tahap 2 & 3 (Aplikasi Setup Update Harga)...")
        jalankan_semua_tahap_indogrosir()

        print("\n" + "="*60)
        logger.info("✅ SEMUA PROSES OTOMASI SELESAI DENGAN SUKSES!")
        print("="*60)

    except Exception as e:
        logger.critical(f"❌ CRITICAL ERROR: {e}", exc_info=True)
    
    input("\nTekan ENTER untuk keluar...")

if __name__ == "__main__":
    if is_admin():
        main()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()