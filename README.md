# Automation Tembak Harga Indogrosir 🚀

Sistem otomatisasi terpadu berbasis Python dan UI Automation untuk mempercepat proses pembaruan harga jual produk (*Update PLU*) di aplikasi Indogrosir.

---

## 📌 Alur Proses Otomasi

Sistem ini menjalankan 3 tahapan utama secara otomatis:

1. **Tahap 1: Login & Update Harga Excel ke HO (`UpdHargaJual.exe`)**
   - Login otomatis menggunakan kredensial yang tersimpan aman di `.env`.
   - Membaca data dari `data/harga.xlsx`.
   - **Validasi Cerdas Penurunan Harga**: Memeriksa harga lama vs harga baru. Jika harga baru lebih kecil (harga turun), sistem akan menandai dan melewatinya secara otomatis untuk mencegah pemblokiran sistem.
   - Menyimpan ke database Oracle dan menutup dialog pop-up konfirmasi via Windows API native (0ms latency).
   - Menampilkan rekapitulasi audit detail di terminal (total berhasil, ditolak, dan daftar PLU).

2. **Tahap 2: Sinkronisasi ke Seluruh Kasir / POS (`UpdateHrgJual.exe`)**
   - Membuka aplikasi setup update harga.
   - Mengklik tombol **`SEND TO POS`** (`BtnUpdate`) secara presisi tanpa tombol buta.
   - Menyetujui konfirmasi dialog secara instan.
   - Memantau label status (`lblStatus`) secara real-time hingga status `"DONE"`.
   - Menutup aplikasi via tombol `Close`.

3. **Tahap 3: Sinkronisasi ke SPI (`UpdateHrgJual.exe`)**
   - Membuka kembali aplikasi setup update harga.
   - Mengklik tombol **`SEND TO SPI`** (`BtnSPI`) secara langsung.
   - Menyetujui dialog konfirmasi.
   - Memantau proses hingga `"DONE"`.
   - Menutup aplikasi via tombol `Close`.

---

## 🛠️ Persyaratan Sistem

- **Sistem Operasi**: Windows 10 / 11 (64-bit).
- **Python**: Python 3.10+ (Direkomendasikan Python 3.13).
- **Hak Akses**: Wajib dijalankan dengan izin **Administrator** (*Run as Administrator*).

---

## 📦 Instalasi & Pengaturan

1. **Clone Repository**:
   ```bash
   git clone https://github.com/edpspibdl/AUTOMATION-TEMBAK-HARGA.git
   cd AUTOMATION-TEMBAK-HARGA
   ```

2. **Install Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfigurasi Akun (`.env`)**:
   Salin template `.env.example` menjadi `.env`:
   ```bash
   copy .env.example .env
   ```
   Buka file `.env` dan sesuaikan kredensial login Indogrosir Anda:
   ```env
   LOGIN_PERINTAH=kode_bagian_anda
   LOGIN_PASSWORD=password_anda
   LOGIN_USER_ID=user_id_anda
   ```

4. **Siapkan Data Excel**:
   Pastikan file `data/harga.xlsx` memiliki kolom:
   - `PLU` : Kode PLU produk
   - `HARGA` : Harga jual baru yang diinginkan

---

## 🚀 Cara Menjalankan

Jalankan script utama melalui terminal atau command prompt:
```bash
python main.py
```

*Catatan: Saat script sedang berjalan, hindari mengetik atau mengklik aplikasi lain agar fokus input keyboard tetap stabil.*

---

## 📄 Struktur Direktori

```text
AUTOMATION-TEMBAK-HARGA/
├── data/
│   └── harga.xlsx          # Data input harga baru
├── log/
│   └── run.log             # Riwayat eksekusi (otomatis dibuat)
├── src/
│   ├── login.py            # Modul login dinamis (.env)
│   ├── update_harga.py     # Modul Tahap 1 (Update PLU + Rekap)
│   └── aplikasi_kedua.py   # Modul Tahap 2 & 3 (SEND TO POS & SPI)
├── .env.example            # Template kredensial aman
├── .gitignore              # Proteksi file kredensial & log
├── main.py                 # Entrypoint otomasi utama
├── README.md               # Dokumentasi proyek
└── requirements.txt        # Daftar pustaka Python
```
