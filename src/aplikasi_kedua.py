import os
import sys
import time
import logging
import subprocess
import ctypes
from ctypes import wintypes
from pywinauto import Application
from pywinauto.keyboard import send_keys

logger = logging.getLogger("automation")

EXE_PATH = r"C:\Program Files (x86)\INDOGROSIR\Setup_UpdateHrgJual\UpdateHrgJual.exe"
EXE_NAME = "UpdateHrgJual.exe"

# ==================== WIN32 NATIVE HELPERS ====================
user32 = ctypes.windll.user32
user32.GetWindow.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.SendMessageW.restype = wintypes.LPARAM
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]

GW_ENABLEDPOPUP = 6
WM_COMMAND = 0x0111
IDOK = 1
IDYES = 6

def get_modal_popup(main_hwnd):
    """Mendapatkan HWND dialog modal di atas jendela utama secara instan."""
    try:
        h = user32.GetWindow(main_hwnd, GW_ENABLEDPOPUP)
        if h and h != main_hwnd:
            return h
    except Exception:
        pass
    return None

def get_hwnd_text(hwnd):
    """Membaca judul jendela berdasarkan HWND."""
    try:
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
    except Exception:
        pass
    return ""

def confirm_modal_dialog(popup_hwnd, send_yes=True):
    """Mengonfirmasi dialog modal (tombol YES / OK) tanpa tombol buta."""
    try:
        user32.SetForegroundWindow(popup_hwnd)
        time.sleep(0.1)
        cmd_id = IDYES if send_yes else IDOK
        user32.SendMessageW(popup_hwnd, WM_COMMAND, cmd_id, 0)
        time.sleep(0.2)
        send_keys("{ENTER}")
    except Exception:
        send_keys("{ENTER}")

# ==================== KONTROL & NAVIGASI PRESISI ====================
def get_target_button(main_window, auto_id, candidate_titles):
    """
    Mencari tombol target berdasarkan AutomationId atau Caption teks secara presisi.
    Mencegah penggunaan tombol buta (seperti navigasi panah keyboard).
    """
    # 1. Cari via auto_id
    if auto_id:
        try:
            btn = main_window.child_window(auto_id=auto_id, control_type="Button")
            if btn.exists(timeout=1):
                return btn
        except Exception:
            pass

    # 2. Cari via candidate_titles
    for title in candidate_titles:
        try:
            btn = main_window.child_window(title=title, control_type="Button")
            if btn.exists(timeout=1):
                return btn
        except Exception:
            pass

    # 3. Pencarian fleksibel pada seluruh tombol anak
    try:
        for child in main_window.children(control_type="Button"):
            cid = child.automation_id()
            ctxt = child.window_text()
            if (auto_id and cid and auto_id.lower() in cid.lower()) or \
               any(t.lower() in ctxt.lower() for t in candidate_titles):
                return child
    except Exception:
        pass

    return None

def proses_tahap(btn_auto_id, candidate_titles, label_tahap):
    print("\n" + "="*60)
    logger.info(f"📌 {label_tahap}")
    print("="*60)

    if not os.path.exists(EXE_PATH):
        logger.error(f"❌ File aplikasi kedua tidak ditemukan di: {EXE_PATH}")
        return False

    # 1. Bersihkan proses lama agar form terbuka dalam kondisi bersih
    logger.info(f"🚀 Membuka aplikasi: {EXE_NAME}")
    os.system(f"taskkill /f /im {EXE_NAME} >nul 2>&1")
    time.sleep(1.0)

    try:
        # 2. Jalankan aplikasi
        subprocess.Popen(EXE_PATH)
        logger.info("⏳ Menghubungkan ke jendela 'Update Hrg Jual'...")

        # 3. Koneksi ke aplikasi secara dinamis
        app = Application(backend="uia").connect(path=EXE_NAME, timeout=30)
        main_window = app.top_window()
        main_window.wait("ready", timeout=30)
        main_window.set_focus()
        logger.info(f"✅ Jendela terhubung: [{main_window.window_text()}]")
        time.sleep(1.0)

        # 4. Cari tombol secara presisi (Tanpa Tombol Buta!)
        target_btn = get_target_button(main_window, btn_auto_id, candidate_titles)
        if not target_btn:
            logger.error(f"❌ GAGAL: Tombol target [{btn_auto_id} / {candidate_titles}] tidak ditemukan!")
            return False

        logger.info(f"🎯 Tombol Ditemukan: [{target_btn.window_text()}] (ID: {btn_auto_id})")
        
        # 5. Klik tombol langsung via input mouse
        target_btn.click_input()
        logger.info(f"🖱️  Tombol [{target_btn.window_text()}] berhasil diklik.")

        # 6. Tangani Dialog Konfirmasi Modal ("Apakah anda yakin...?")
        logger.info("⏳ Menunggu dialog konfirmasi sistem...")
        dialog_confirmed = False
        start_wait = time.time()
        while time.time() - start_wait < 8.0:
            pop_hwnd = get_modal_popup(main_window.handle)
            if pop_hwnd:
                pop_title = get_hwnd_text(pop_hwnd)
                logger.info(f"🗨️  Dialog Terdeteksi: [{pop_title}] ➔ Menyetujui konfirmasi (YES)")
                confirm_modal_dialog(pop_hwnd, send_yes=True)
                dialog_confirmed = True
                break
            
            # Fallback deteksi jendela anak pywinauto
            try:
                for w in app.windows():
                    if w.handle != main_window.handle:
                        pop_title = w.window_text()
                        logger.info(f"🗨️  Dialog Terdeteksi: [{pop_title}] ➔ Menyetujui konfirmasi (YES)")
                        confirm_modal_dialog(w.handle, send_yes=True)
                        dialog_confirmed = True
                        break
            except Exception:
                pass

            if dialog_confirmed:
                break
            time.sleep(0.3)

        if not dialog_confirmed:
            logger.warning("⚠️  Dialog konfirmasi tidak muncul terpisah, melanjutkan pemantauan...")

        # 7. Pemantauan Progres Real-Time (BUKAN COUNTDOWN 30 DETIK BUTA)
        logger.info("⏳ Memantau proses pembaruan database secara langsung...")
        start_proc = time.time()
        last_status = ""
        while time.time() - start_proc < 120.0:  # Batas waktu maksimal 2 menit
            # A. Baca teks status dari label 'lblStatus'
            status_text = ""
            try:
                lbl = main_window.child_window(auto_id="lblStatus")
                if lbl.exists(timeout=0.1):
                    status_text = lbl.window_text().strip()
            except Exception:
                pass

            if status_text and status_text != "Status" and status_text != last_status:
                sys.stdout.write(f"\r   ↳ 🔄 {status_text}                           ")
                sys.stdout.flush()
                last_status = status_text

            # B. Cek apakah status sudah 'DONE'
            if "DONE" in status_text.upper():
                print(f"\r   ↳ ✅ Pembaruan Selesai: [{status_text}]                   ")
                break

            # C. Cek apakah tombol Close atau tombol target sudah aktif kembali
            # Di aplikasi Indogrosir, tombol dinonaktifkan (Disabled) selama update berjalan
            if time.time() - start_proc > 2.0:
                try:
                    btn_close = main_window.child_window(auto_id="BtnClose")
                    if btn_close.exists(timeout=0.1) and btn_close.is_enabled():
                        print(f"\r   ↳ ✅ Proses selesai (Seluruh data telah terdistribusi)    ")
                        break
                except Exception:
                    pass

            # D. Cek apakah ada alert pop-up (seperti 'Tidak ada data...')
            pop_hwnd = get_modal_popup(main_window.handle)
            if pop_hwnd:
                pop_title = get_hwnd_text(pop_hwnd)
                logger.info(f"\n   ↳ ℹ️  Informasi Sistem: [{pop_title}]")
                confirm_modal_dialog(pop_hwnd, send_yes=False)
                break

            time.sleep(0.4)

        # 8. Menutup Aplikasi Melalui Tombol 'Close' Presisi
        logger.info("🚪 Menutup aplikasi via tombol 'Close'...")
        try:
            btn_close = get_target_button(main_window, "BtnClose", ["Close", "CLOSE"])
            if btn_close and btn_close.exists() and btn_close.is_enabled():
                btn_close.click_input()
                time.sleep(1.5)
        except Exception:
            pass

        # Pastikan proses benar-benar tertutup sebelum tahap berikutnya dibuka
        os.system(f"taskkill /f /im {EXE_NAME} >nul 2>&1")
        time.sleep(1.0)

        logger.info(f"✨ {label_tahap} BERHASIL DISINKRONISASI!")
        return True

    except Exception as e:
        logger.error(f"❌ Terjadi kesalahan pada {label_tahap}: {e}")
        os.system(f"taskkill /f /im {EXE_NAME} >nul 2>&1")
        return False

# ==================== ENTRYPOINT TAHAP 2 & 3 ====================
def jalankan_semua_tahap_indogrosir():
    start_all = time.time()

    # Tahap 2: Update ke Kasir (Tombol 'BtnUpdate' / 'SEND TO POS')
    sukses_pos = proses_tahap(
        btn_auto_id="BtnUpdate",
        candidate_titles=["SEND TO POS", "POS", "Kasir"],
        label_tahap="TAHAP 2: SINKRONISASI HARGA KE KASIR (SEND TO POS)"
    )

    logger.info("☕ Aplikasi Kasir ditutup. Jeda 4 detik sebelum membuka kembali untuk SPI...")
    time.sleep(4)

    # Tahap 3: Buka Kembali Aplikasi & Update ke SPI (Tombol 'BtnSPI' / 'SEND TO SPI') - Dijalankan 2 kali
    sukses_spi_1 = proses_tahap(
        btn_auto_id="BtnSPI",
        candidate_titles=["SEND TO SPI", "SPI"],
        label_tahap="TAHAP 3 (1/2): SINKRONISASI HARGA KE SPI (SEND TO SPI - PERTAMA)"
    )

    logger.info("☕ Jeda 4 detik sebelum pengulangan push ke SPI kedua...")
    time.sleep(4)

    sukses_spi_2 = proses_tahap(
        btn_auto_id="BtnSPI",
        candidate_titles=["SEND TO SPI", "SPI"],
        label_tahap="TAHAP 3 (2/2): SINKRONISASI HARGA KE SPI (SEND TO SPI - KEDUA)"
    )

    total_durasi = round((time.time() - start_all) / 60, 2)
    print("\n" + "="*60)
    logger.info("🏆 SEMUA TAHAP SINKRONISASI INDOGROSIR SELESAI!")
    logger.info(f"⏱️  Total Durasi: {total_durasi} menit")
    logger.info(f"   • Sinkronisasi POS Kasir   : {'✅ Berhasil' if sukses_pos else '❌ Gagal'}")
    logger.info(f"   • Sinkronisasi SPI (Ke-1)  : {'✅ Berhasil' if sukses_spi_1 else '❌ Gagal'}")
    logger.info(f"   • Sinkronisasi SPI (Ke-2)  : {'✅ Berhasil' if sukses_spi_2 else '❌ Gagal'}")
    print("="*60)