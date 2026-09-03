import os
import re
import sys
import time
import logging
import ctypes
from ctypes import wintypes
import pandas as pd
from pywinauto.keyboard import send_keys

logger = logging.getLogger("automation")

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

def get_modal_popup_hwnd(main_hwnd):
    """Mendapatkan HWND dari modal pop-up yang sedang menempel pada jendela utama."""
    try:
        popup_hwnd = user32.GetWindow(main_hwnd, GW_ENABLEDPOPUP)
        if popup_hwnd and popup_hwnd != main_hwnd:
            return popup_hwnd
    except Exception:
        pass
    return None

def get_hwnd_text(hwnd):
    """Membaca judul teks jendela berdasarkan HWND."""
    try:
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
    except Exception:
        pass
    return ""

def dismiss_popup_by_hwnd(popup_hwnd):
    """Menutup dialog modal secara instan via pesan Win32 dan keyboard."""
    try:
        user32.SetForegroundWindow(popup_hwnd)
        time.sleep(0.1)
        # 1. Kirim pesan klik tombol OK langsung ke prosedur dialog
        user32.SendMessageW(popup_hwnd, WM_COMMAND, IDOK, 0)
        time.sleep(0.2)
        # 2. Backup dengan send_keys Enter
        send_keys("{ENTER}")
    except Exception:
        send_keys("{ENTER}")

# ==================== PYWINAUTO HELPERS ====================
def get_control(win, auto_id=None, title=None, control_type=None):
    """Mencari child window berdasarkan auto_id atau title secara aman."""
    try:
        kwargs = {}
        if auto_id: kwargs["auto_id"] = auto_id
        if title: kwargs["title"] = title
        if control_type: kwargs["control_type"] = control_type
        ctrl = win.child_window(**kwargs)
        if ctrl.exists(timeout=1):
            return ctrl
    except Exception:
        pass
    return None

def parse_harga_lama(raw_text):
    """
    Mem-parsing teks harga lama dari lblHargaOld.
    Aplikasi VB.NET menggunakan FormatNumber(nHargaOld, 2) yang selalu menghasilkan
    2 angka desimal di belakang, misalnya: '211,700.00' atau '211.700,00'.
    """
    if not raw_text:
        return None
    text = str(raw_text).strip()
    
    # Cek pola angka dengan pemisah desimal (. atau ,) diikuti 2 digit di akhir
    match = re.search(r"^(.*?)[.,](\d{2})$", text)
    if match:
        main_part = match.group(1)
        dec_part = match.group(2)
        clean_main = re.sub(r"[^\d]", "", main_part)
        if clean_main:
            return float(f"{clean_main}.{dec_part}")

    clean = re.sub(r"[^\d]", "", text)
    return float(clean) if clean else None

def reset_form(win):
    """
    Mereset form ke kondisi bersih dengan menekan tombol 'NEW' (btnNew),
    sehingga field PLU kosong dan siap menerima input berikutnya.
    """
    # 1. Jika ada pop-up tersisa yang menahan jendela utama, tutup terlebih dahulu
    popup_hwnd = get_modal_popup_hwnd(win.handle)
    if popup_hwnd:
        dismiss_popup_by_hwnd(popup_hwnd)
        time.sleep(0.5)

    # 2. Klik tombol NEW
    try:
        btn_new = get_control(win, auto_id="btnNew", control_type="Button")
        if not btn_new:
            btn_new = get_control(win, title="NEW", control_type="Button")
        
        if btn_new and btn_new.is_enabled():
            btn_new.click_input()
            time.sleep(0.5)
            return True
    except Exception:
        pass

    # Fallback navigasi keyboard
    try:
        send_keys("{LEFT}{LEFT}{ENTER}")
        time.sleep(0.5)
        return True
    except Exception:
        pass
    return False

def check_and_handle_popup(app, main_win, timeout=2.0, poll_interval=0.05):
    """
    Mendeteksi apakah ada pop-up dialog (seperti 'STOP' atau 'Informasi').
    Menutup pop-up secara instan (50ms) dan mengembalikan (judul_popup, pesan_popup).
    """
    main_hwnd = main_win.handle
    start = time.time()
    while time.time() - start < timeout:
        # 1. Deteksi cepat & akurat via Win32 API (0ms latency)
        popup_hwnd = get_modal_popup_hwnd(main_hwnd)
        if popup_hwnd:
            title = get_hwnd_text(popup_hwnd)
            dismiss_popup_by_hwnd(popup_hwnd)
            time.sleep(0.1)
            return title.strip(), "OK"

        # 2. Fallback deteksi via pywinauto windows
        try:
            for w in app.windows():
                if w.handle != main_hwnd:
                    title = w.window_text()
                    dismiss_popup_by_hwnd(w.handle)
                    time.sleep(0.1)
                    return title.strip(), "OK"
        except Exception:
            pass

        time.sleep(poll_interval)
    return None, None


# ==================== MAIN LOGIC ====================
def update_harga(app):
    print("\n" + "="*50)
    logger.info("🚀 TAHAP 1: PROSES UPDATE HARGA DARI EXCEL")
    print("="*50)

    # 1. Pastikan Window Aktif
    try:
        win = app.top_window()
        win.wait("ready", timeout=20)
        win.set_focus()
        logger.info(f"✅ Terhubung ke jendela: {win.window_text()}")
    except Exception as e:
        logger.error(f"❌ GAGAL: Tidak bisa menemukan jendela aplikasi. {e}")
        return

    # 2. Load Data Excel
    file_path = "data/harga.xlsx"
    if not os.path.exists(file_path):
        logger.error(f"❌ GAGAL: File excel tidak ditemukan di '{file_path}'!")
        return

    try:
        df = pd.read_excel(file_path, dtype=str)
        df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
        
        if "PLU" not in df.columns or "HARGA" not in df.columns:
            logger.error("❌ GAGAL: Kolom 'PLU' atau 'HARGA' tidak ditemukan di excel!")
            return

        total_data = len(df)
        logger.info(f"📂 File ditemukan: {file_path}")
        logger.info(f"📊 Total data yang akan diproses: {total_data} Baris")
        print("-" * 50)
    except Exception as e:
        logger.error(f"❌ GAGAL membaca file excel: {e}")
        return

    # Statistik dan Pelacak Detail
    list_berhasil = []
    list_harga_turun = []
    list_tidak_ada = []
    list_error = []
    start_time = time.time()

    # 3. Looping Data
    for i, row in df.iterrows():
        plu = str(row["PLU"]).strip() if pd.notna(row["PLU"]) else ""
        raw_harga = str(row["HARGA"]).strip() if pd.notna(row["HARGA"]) else ""

        # Validasi format harga
        try:
            harga_num = int(float(raw_harga))
            harga = str(harga_num)
        except Exception:
            harga = None

        pos_str = f"[{i+1:02d}/{total_data:02d}]"

        if not plu or not harga:
            logger.warning(f"⏩ {pos_str} SKIPPED: PLU '{plu}' atau harga '{raw_harga}' kosong/tidak valid.")
            list_error.append({"plu": plu or "-", "alasan": f"Data Excel kosong/tidak valid (Harga: '{raw_harga}')"})
            continue

        try:
            # 0. Tutup sisa pop-up lama jika ada
            leftover = get_modal_popup_hwnd(win.handle)
            if leftover:
                dismiss_popup_by_hwnd(leftover)
                time.sleep(0.2)

            # 1. Pastikan form dalam kondisi bersih (tombol NEW)
            reset_form(win)
            time.sleep(0.2)

            # 2. Input PLU
            win.set_focus()
            win.type_keys(plu, with_spaces=True)
            time.sleep(0.2)
            win.type_keys("{ENTER}")
            time.sleep(0.4)

            # 3. Cek pop-up cegatan setelah input PLU (misal: "Data Tidak Ada !!" atau "Status Tag = X/Q/Z !!")
            pop_title, pop_msg = check_and_handle_popup(app, win, timeout=0.3, poll_interval=0.05)
            if pop_title:
                logger.warning(f"⚠️  {pos_str} PLU {plu} -> DITOLAK SISTEM [{pop_title}]: {pop_msg}")
                list_tidak_ada.append({"plu": plu, "alasan": f"{pop_title} - {pop_msg}"})
                reset_form(win)
                continue

            # 4. BACA HARGA LAMA DARI FORM (lblHargaOld) UNTUK VALIDASI PROAKTIF
            harga_lama_val = None
            raw_old_text = ""
            try:
                lbl_old = get_control(win, auto_id="lblHargaOld", control_type="Text")
                if lbl_old:
                    raw_old_text = lbl_old.window_text().strip()
                    harga_lama_val = parse_harga_lama(raw_old_text)
            except Exception as e:
                logger.debug(f"Info: Tidak dapat membaca lblHargaOld: {e}")

            hl_str = f"Rp {harga_lama_val:,.0f}" if harga_lama_val is not None else "(Tidak Terbaca)"
            hb_str = f"Rp {harga_num:,.0f}"

            logger.info(f"▶ {pos_str} PLU {plu} | Lama: {hl_str} ➔ Baru: {hb_str}")

            # 5. CEK APAKAH HARGA BARU LEBIH KECIL DARI HARGA LAMA
            if harga_lama_val is not None and harga_num < harga_lama_val:
                selisih = harga_lama_val - harga_num
                logger.warning(
                    f"   ↳ 🛑 STATUS: DITOLAK (HARGA TURUN: Baru {hb_str} < Lama {hl_str} | Selisih: -Rp {selisih:,.0f})"
                )
                list_harga_turun.append({
                    "plu": plu,
                    "lama": harga_lama_val,
                    "baru": harga_num,
                    "selisih": selisih
                })
                reset_form(win)
                continue

            # 6. Input Harga Baru & Tekan ENTER (Otomatis memvalidasi & memindahkan fokus ke tombol SAVE)
            win.set_focus()
            win.type_keys(harga, with_spaces=True)
            time.sleep(0.2)
            win.type_keys("{ENTER}")
            time.sleep(0.3)

            # 7. Cek apakah ada alert STOP setelah input harga (Safety Net)
            pop_title, pop_msg = check_and_handle_popup(app, win, timeout=0.3, poll_interval=0.05)
            if pop_title and "STOP" in pop_title.upper():
                logger.warning(f"   ↳ 🛑 STATUS: DITOLAK SISTEM [{pop_title}]: {pop_msg}")
                list_harga_turun.append({
                    "plu": plu,
                    "lama": harga_lama_val or 0,
                    "baru": harga_num,
                    "selisih": (harga_lama_val or 0) - harga_num
                })
                reset_form(win)
                continue

            # 8. Eksekusi Simpan dengan menekan ENTER pada tombol SAVE yang sudah fokus
            logger.info(f"   ↳ ⏳ Sedang simpan database & proses email notifikasi...")
            win.type_keys("{ENTER}")

            # 9. Konfirmasi Pop-up Hasil Simpan ("Informasi" -> "Perubahan Harga Jual Sudah Di Simpan dan Di Email !!")
            pop_title, pop_msg = check_and_handle_popup(app, win, timeout=35.0, poll_interval=0.05)
            if pop_title:
                logger.info(f"   ↳ ✅ STATUS: BERHASIL DISIMPAN ({pop_title})")
            else:
                leftover = get_modal_popup_hwnd(win.handle)
                if leftover:
                    dismiss_popup_by_hwnd(leftover)
                logger.info(f"   ↳ ✅ STATUS: BERHASIL DISIMPAN")

            list_berhasil.append({
                "plu": plu,
                "lama": harga_lama_val,
                "baru": harga_num
            })

            # 10. Siapkan form untuk baris berikutnya
            reset_form(win)
            time.sleep(0.2)

        except Exception as e:
            logger.error(f"   ↳ ❌ Error baris {i+1} (PLU {plu}): {e}")
            list_error.append({"plu": plu, "alasan": str(e)})
            leftover = get_modal_popup_hwnd(win.handle)
            if leftover:
                dismiss_popup_by_hwnd(leftover)
            send_keys("{ESC}")
            reset_form(win)
            time.sleep(0.3)
            continue

    # 4. Ringkasan Akhir yang Sangat Informatif
    end_time = time.time()
    durasi_total = end_time - start_time
    menit = int(durasi_total // 60)
    detik = int(durasi_total % 60)
    durasi_str = f"{menit} Menit {detik} Detik" if menit > 0 else f"{round(durasi_total, 1)} Detik"

    total_sukses = len(list_berhasil)
    total_turun = len(list_harga_turun)
    total_tag = len(list_tidak_ada)
    total_err = len(list_error)

    pct_sukses = round((total_sukses / total_data) * 100, 1) if total_data > 0 else 0
    pct_turun = round((total_turun / total_data) * 100, 1) if total_data > 0 else 0
    pct_tag = round((total_tag / total_data) * 100, 1) if total_data > 0 else 0
    pct_err = round((total_err / total_data) * 100, 1) if total_data > 0 else 0

    print("\n" + "="*70)
    logger.info("📊 REKAPITULASI HASIL UPDATE HARGA INDOGROSIR (TAHAP 1)")
    print("="*70)
    logger.info(f"📁 Sumber File       : {file_path}")
    logger.info(f"📊 Total Data        : {total_data} PLU")
    logger.info(f"⏱️  Durasi Pengerjaan : {durasi_str}")
    print("-" * 70)
    logger.info(f"✅ BERHASIL DIUPDATE     : {total_sukses:2d} PLU  ({pct_sukses:>5}%)")
    logger.info(f"🛑 DITOLAK (HARGA TURUN) : {total_turun:2d} PLU  ({pct_turun:>5}%)")
    logger.info(f"⚠️  DITOLAK (TAG/NOT FOUND): {total_tag:2d} PLU  ({pct_tag:>5}%)")
    logger.info(f"❌ ERROR/GAGAL LAINNYA   : {total_err:2d} PLU  ({pct_err:>5}%)")
    print("-" * 70)

    # Tampilkan Rincian PLU yang Ditolak / Gagal agar operator langsung tahu tindakannya
    if list_harga_turun:
        logger.warning("📋 RINCIAN PLU YANG DITOLAK KARENA HARGA LEBIH KECIL:")
        for idx, item in enumerate(list_harga_turun, 1):
            lama_f = f"Rp {item['lama']:,.0f}" if item['lama'] else "-"
            baru_f = f"Rp {item['baru']:,.0f}"
            selisih_f = f"Rp {item['selisih']:,.0f}" if item.get('selisih') else "-"
            logger.warning(f"   {idx:2d}. PLU {item['plu']} | Lama: {lama_f:>13} ➔ Baru: {baru_f:>13} (Turun: {selisih_f})")
        print("-" * 70)

    if list_tidak_ada:
        logger.warning("📋 RINCIAN PLU YANG DITOLAK (TAG DIBLOKIR / TIDAK TERDAFTAR):")
        for idx, item in enumerate(list_tidak_ada, 1):
            logger.warning(f"   {idx:2d}. PLU {item['plu']} | Alasan: {item['alasan']}")
        print("-" * 70)

    if list_error:
        logger.error("📋 RINCIAN PLU DENGAN ERROR LAINNYA:")
        for idx, item in enumerate(list_error, 1):
            logger.error(f"   {idx:2d}. PLU {item['plu']} | Error: {item['alasan']}")
        print("-" * 70)

    if total_sukses == total_data:
        logger.info("🎉 SEMPURNA! Semua harga PLU berhasil diupdate 100% tanpa ada kendala!")

    print("="*70)

    # 5. Menutup Aplikasi Pertama
    logger.info("🚪 Menutup aplikasi UpdHargaJual...")
    try:
        btn_exit = get_control(win, auto_id="btnExit", control_type="Button")
        if not btn_exit:
            btn_exit = get_control(win, title="EXIT", control_type="Button")
            
        if btn_exit and btn_exit.exists():
            btn_exit.click_input()
        else:
            win.type_keys("%{F4}")
    except Exception:
        send_keys("%{F4}")

    logger.info("⏳ Jeda transisi ke aplikasi berikutnya...")
    time.sleep(5)