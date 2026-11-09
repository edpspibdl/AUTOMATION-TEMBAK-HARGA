import os
import sys
import time
import logging
import ctypes
from datetime import datetime
from dotenv import load_dotenv

# Import main function
from main import main as run_automation, is_admin

load_dotenv()

def setup_scheduler_logger():
    """Inisialisasi logger khusus service / scheduler."""
    os.makedirs("log", exist_ok=True)
    logger = logging.getLogger("scheduler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # File Handler
    fh = logging.FileHandler("log/scheduler.log", encoding="utf-8")
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

def parse_schedule_times():
    """
    Membaca jadwal jam dari .env.
    Format contoh di .env:
    SCHEDULE_JAM=06:00, 12:00, 18:00
    Default jika kosong: 06:00
    """
    raw = os.getenv("SCHEDULE_JAM", "06:00")
    times = [t.strip() for t in raw.split(",") if t.strip()]
    valid_times = []
    for t in times:
        try:
            # Validasi format HH:MM
            datetime.strptime(t, "%H:%M")
            valid_times.append(t)
        except ValueError:
            print(f"⚠️  Format jam tidak valid: '{t}'. Gunakan format HH:MM (contoh: 07:30)")
    return valid_times if valid_times else ["06:00"]

def start_scheduler():
    logger = setup_scheduler_logger()
    scheduled_times = parse_schedule_times()

    print("=" * 60)
    logger.info("🕒 SCHEDULER SERVICE OTOMASI INDOGROSIR AKTIF")
    logger.info(f"📅 Jam Eksekusi Terjadwal: {', '.join(scheduled_times)}")
    logger.info("💡 Tekan Ctrl+C di jendela ini untuk menghentikan scheduler.")
    print("=" * 60)

    last_executed = None

    while True:
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_minute_key = now.strftime("%Y-%m-%d %H:%M")

            # Cek apakah jam saat ini cocok dengan salah satu jadwal dan belum dijalankan pada menit ini
            if current_time in scheduled_times and last_executed != current_minute_key:
                logger.info(f"⏰ Waktu tercapai [{current_time}]! Memulai proses otomasi otomatis...")
                last_executed = current_minute_key
                
                try:
                    # Jalankan otomasi secara non-interaktif
                    run_automation(interactive=False)
                    logger.info("🏁 Eksekusi otomasi selesai. Kembali memantau jadwal berikutnya...")
                except Exception as err:
                    logger.error(f"❌ Terjadi kesalahan saat eksekusi otomatis: {err}", exc_info=True)
                
                print("\n" + "=" * 60)
                logger.info(f"⏳ Menunggu jadwal berikutnya: {', '.join(scheduled_times)}")
                print("=" * 60)

            # Istirahat 5 detik sebelum cek berikutnya
            time.sleep(5)

        except KeyboardInterrupt:
            logger.info("🛑 Scheduler dihentikan oleh pengguna.")
            break
        except Exception as e:
            logger.error(f"⚠️ Error loop scheduler: {e}")
            time.sleep(10)

if __name__ == "__main__":
    if is_admin():
        start_scheduler()
    else:
        # Minta hak Administrator jika belum
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

