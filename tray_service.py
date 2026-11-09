import os
import sys
import time
import logging
import threading
import ctypes
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item

# Import fungsi utama otomasi
from main import main as run_automation, is_admin

# Setup environment & base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
os.makedirs("log", exist_ok=True)

# ==================== LOGGER TRAY ====================
def setup_tray_logger():
    logger = logging.getLogger("tray_service")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler("log/tray_service.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fh_fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fh_fmt)
    logger.addHandler(ch)

    return logger

logger = setup_tray_logger()

# ==================== STATE GLOBAL ====================
is_running = False
current_status = "Standby (Menunggu Jadwal)"
last_run_info = "Belum pernah dijalankan"
lock = threading.Lock()
tray_icon = None

# ==================== GENERATOR ICON TRAY ====================
def create_tray_icon_image(state="idle"):
    """
    Membuat icon system tray dinamis menggunakan Pillow.
    - idle: Lingkaran biru gelap dengan teks 'IDG' putih.
    - running: Lingkaran hijau menyala dengan teks 'RUN'.
    """
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if state == "running":
        bg_color = (46, 204, 113)   # Hijau
        accent_color = (39, 174, 96)
        text = "RUN"
    else:
        bg_color = (31, 110, 212)   # Biru Indogrosir
        accent_color = (21, 85, 170)
        text = "IDG"

    # Background lingkaran berbingkai halus
    draw.ellipse([2, 2, size - 3, size - 3], fill=bg_color, outline=accent_color, width=2)

    # Teks label icon di tengah
    try:
        # Gunakan font default jika font ttf tidak tersedia
        draw.text((size // 2, size // 2), text, fill=(255, 255, 255), anchor="mm")
    except Exception:
        draw.text((size // 4, size // 3), text, fill=(255, 255, 255))

    return image

# ==================== PARSER JADWAL .ENV ====================
def get_scheduled_times():
    """
    Membaca ulang file .env secara dinamis.
    Pengguna bisa mengubah file .env tanpa harus me-restart service.
    """
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
    raw = os.getenv("SCHEDULE_JAM", "06:00")
    times = [t.strip() for t in raw.split(",") if t.strip()]
    valid_times = []
    for t in times:
        try:
            datetime.strptime(t, "%H:%M")
            valid_times.append(t)
        except ValueError:
            pass
    return valid_times if valid_times else ["06:00"]

# ==================== EKSEKUSI OTOMASI ====================
def execute_job(source="Jadwal"):
    global is_running, current_status, last_run_info, tray_icon

    if is_running:
        if tray_icon:
            tray_icon.notify("Otomasi sedang berjalan, mohon tunggu hingga proses selesai.", "Indogrosir Otomasi")
        return

    with lock:
        is_running = True
        current_status = f"Sedang Berjalan ({source})..."
        if tray_icon:
            tray_icon.icon = create_tray_icon_image("running")
            tray_icon.title = f"Otomasi Indogrosir - Sedang Berjalan ({source})..."
            try:
                tray_icon.notify(
                    f"Memulai proses sinkronisasi harga & SPI ({source})...",
                    "Otomasi Indogrosir Dimulai"
                )
            except Exception:
                pass

        logger.info(f"🚀 Memulai eksekusi otomasi dari sumber: [{source}]")
        start_time = time.time()
        success = False

        try:
            # Jalankan otomatis tanpa prompt interaktif
            run_automation(interactive=False)
            success = True
            durasi = round(time.time() - start_time, 1)
            last_run_info = f"{datetime.now().strftime('%d/%m %H:%M:%S')} (Sukses - {durasi}s)"
            current_status = "Standby (Sukses)"
            logger.info(f"✅ Eksekusi [{source}] selesai dengan sukses dalam {durasi} detik.")
            if tray_icon:
                try:
                    tray_icon.notify(
                        "Semua tahap (Login, POS, dan 2x Push SPI) berhasil!",
                        "Otomasi Indogrosir Sukses"
                    )
                except Exception:
                    pass
        except Exception as e:
            durasi = round(time.time() - start_time, 1)
            last_run_info = f"{datetime.now().strftime('%d/%m %H:%M:%S')} (Gagal)"
            current_status = f"Gagal: {e}"
            logger.error(f"❌ Eksekusi [{source}] gagal: {e}", exc_info=True)
            if tray_icon:
                try:
                    tray_icon.notify(
                        f"Gagal saat proses: {str(e)[:100]}",
                        "Otomasi Indogrosir Gagal"
                    )
                except Exception:
                    pass
        finally:
            is_running = False
            if tray_icon:
                tray_icon.icon = create_tray_icon_image("idle")
                tray_icon.title = f"Otomasi Indogrosir - Standby (Jadwal: {', '.join(get_scheduled_times())})"

# ==================== WORKER SCHEDULER ====================
def scheduler_loop():
    """Loop di latar belakang untuk mencocokkan waktu saat ini dengan jadwal."""
    logger.info("🕒 Background Scheduler Loop telah aktif.")
    last_executed_minute = None

    while True:
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_minute_key = now.strftime("%Y-%m-%d %H:%M")
            scheduled_times = get_scheduled_times()

            if current_time in scheduled_times and last_executed_minute != current_minute_key:
                last_executed_minute = current_minute_key
                logger.info(f"⏰ Jam jadwal tercapai [{current_time}]!")
                # Jalankan di thread terpisah agar scheduler tidak freeze
                threading.Thread(target=execute_job, args=("Jadwal",), daemon=True).start()

            time.sleep(5)
        except Exception as e:
            logger.error(f"⚠️ Error pada scheduler loop: {e}")
            time.sleep(10)

# ==================== HANDLER MENU TRAY ====================
def on_run_now(icon, item):
    """Memicu eksekusi manual dari menu tray."""
    threading.Thread(target=execute_job, args=("Manual",), daemon=True).start()

def on_open_log(icon, item):
    """Membuka file log di Notepad."""
    log_path = os.path.join(BASE_DIR, "log", "run.log")
    if not os.path.exists(log_path):
        open(log_path, "a", encoding="utf-8").close()
    os.startfile(log_path)

def on_exit(icon, item):
    """Menghentikan service tray."""
    logger.info("🛑 Service Tray dihentikan oleh pengguna.")
    icon.stop()

# ==================== MENU SYSTEM TRAY (MINIMALIS) ====================
def build_menu():
    return pystray.Menu(
        item("Jalankan Sekarang", on_run_now),
        item("Buka Log", on_open_log),
        pystray.Menu.SEPARATOR,
        item("Keluar", on_exit)
    )

# ==================== MAIN SERVICE ====================
def run_service():
    global tray_icon

    logger.info("=" * 60)
    logger.info("🟢 SERVICE SYSTEM TRAY INDOGROSIR DIMULAI")
    logger.info(f"📁 Direktori: {BASE_DIR}")
    logger.info(f"🕒 Jadwal Jam: {', '.join(get_scheduled_times())}")
    logger.info("=" * 60)

    # Jalankan background scheduler thread
    sched_thread = threading.Thread(target=scheduler_loop, daemon=True)
    sched_thread.start()

    # Inisialisasi System Tray Icon
    icon_image = create_tray_icon_image("idle")
    tray_icon = pystray.Icon(
        name="IndogrosirAuto",
        icon=icon_image,
        title=f"Otomasi Indogrosir - Standby (Jadwal: {', '.join(get_scheduled_times())})",
        menu=build_menu()
    )

    # Jalankan tray icon (blocking hingga icon.stop() dipanggil)
    tray_icon.run()

if __name__ == "__main__":
    if is_admin():
        run_service()
    else:
        # Minta hak Administrator jika belum
        # Jika dijalankan via pythonw, gunakan pythonw agar tidak memunculkan cmd
        exe = sys.executable
        args = f'"{__file__}"'
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)
        sys.exit()

