# Manual Pengguna Radiux

Selamat datang di Manual Pengguna Radiux. Dokumen ini dirancang untuk memandu **Superadmin** dan **Reseller** dalam mengoperasikan Web UI Radiux untuk mengelola FreeRADIUS, NAS, pelanggan, voucher, billing, dan monitoring real-time.

---

## Daftar Isi
1. [Pendahuluan](#pendahuluan)
2. [Panduan Superadmin](#panduan-superadmin)
   - [Manajemen Tenant (Reseller)](#manajemen-tenant-reseller)
   - [Manajemen Paket Global](#manajemen-paket-global)
   - [Manajemen NAS & Vendor Profile](#manajemen-nas--vendor-profile)
   - [Manajemen Saldo & Wallet Reseller](#manajemen-saldo--wallet-reseller)
   - [Audit Logs & Monitoring Sistem](#audit-logs--monitoring-sistem)
3. [Panduan Reseller](#panduan-reseller)
   - [Manajemen Pelanggan (Customers)](#manajemen-pelanggan-customers)
   - [Manajemen Voucher (Prepaid)](#manajemen-voucher-prepaid)
   - [Tagihan & Pembayaran (Postpaid)](#tagihan--pembayaran-postpaid)
   - [Monitoring Sesi Aktif & CoA (Kick User)](#monitoring-sesi-aktif--coa-kick-user)
   - [Dompet Digital & Saldo Reseller](#dompet-digital--saldo-reseller)

---

## Pendahuluan

**Radiux** adalah platform manajemen AAA (Authentication, Authorization, Accounting) modern berbasis web yang terintegrasi langsung dengan database FreeRADIUS. Radiux memisahkan operasional menjadi dua tingkatan peran utama untuk mendukung model bisnis kemitraan/reseller ISP.

---

## Panduan Superadmin

Superadmin memiliki otoritas penuh atas seluruh sistem Radiux. Tugas utama Superadmin adalah memelihara infrastruktur jaringan (NAS), mendefinisikan paket layanan global, serta mengelola akun dan saldo Reseller.

### Manajemen Tenant (Reseller)
Tenant/Reseller adalah mitra bisnis yang menjual kembali layanan internet Anda.
1. **Membuat Reseller Baru**:
   - Masuk ke menu **Tenants** > klik **New Tenant**.
   - Isi nama perusahaan/reseller, kontak, dan status awal (Active).
   - Setelah tenant dibuat, buat akun administrator untuk tenant tersebut melalui menu **Admin Users** > **New Admin**. Pilih role `reseller` dan kaitkan dengan tenant yang baru dibuat.
2. **Mengubah Status Reseller**:
   - Anda dapat menonaktifkan (*suspend*) reseller melalui tombol aksi di tabel Tenants. Reseller yang di-*suspend* tidak akan bisa login ke panel dan seluruh pelanggannya otomatis akan terisolasi atau ikut dinonaktifkan tergantung konfigurasi kebijakan.

### Manajemen Paket Global
Paket global adalah template kecepatan dan harga yang nantinya dapat dijual atau di-generate menjadi voucher oleh reseller.
1. **Membuat Paket**:
   - Masuk ke menu **Packages** > **New Package**.
   - Isi **Package Name** (misal: `10Mbps_Uncapped`).
   - Tentukan parameter kecepatan:
     - **Upload Speed** & **Download Speed** (dalam Mbps/Kbps, contoh: `5M` atau `10M`).
   - Tentukan batas kuota (**Volume Limit** dalam Bytes/GB jika ada, kosongkan jika unlimited).
   - Tentukan **Validity Period** (masa berlaku dalam jam/hari, contoh: `30d` untuk 30 hari).
   - Isi harga dasar (**Price**) dan status (Active).
2. **Sinkronisasi ke FreeRADIUS**:
   - Sistem otomatis menulis aturan paket ke tabel `radgroupcheck` dan `radgroupreply`. Anda tidak perlu merestart FreeRADIUS.

### Manajemen NAS & Vendor Profile
NAS (Network Access Server) adalah router atau access point yang meminta autentikasi ke RADIUS server (contoh: MikroTik, Cisco, Huawei).
1. **Memilih Vendor Profile**:
   - Sebelum mendaftarkan NAS, pastikan profil vendor yang sesuai telah tersedia di menu **Vendor Profiles**. Profil ini memetakan bagaimana parameter rate-limit (misal: `Mikrotik-Rate-Limit` untuk MikroTik) dikirimkan.
2. **Mendaftarkan Perangkat NAS Baru**:
   - Masuk ke menu **NAS** > **Add NAS**.
   - Isi **NAS Name** (identifikasi unik) dan **IP Address** (IP lokal router yang terhubung ke RADIUS).
   - Pilih **Vendor Profile** dari dropdown.
   - Masukkan **Shared Secret** (kunci keamanan untuk enkripsi paket RADIUS). Radiux menyimpan secret ini terenkripsi di database demi keamanan.
   - Klik **Save**. Router sekarang siap mengirimkan request Autentikasi dan Accounting ke port `1812` & `1813` UDP server.

### Manajemen Saldo & Wallet Reseller
Reseller membutuhkan saldo untuk dapat mendaftarkan pelanggan postpaid atau men-generate voucher prepaid.
1. **Top-Up Saldo Reseller**:
   - Masuk ke menu **Tenants** > pilih Tenant yang dituju.
   - Klik tombol **Top Up**.
   - Masukkan jumlah saldo (IDR) dan catatan (misal: "Transfer Bank BCA").
   - Klik **Submit**. Saldo reseller akan langsung bertambah dan transaksi tercatat di riwayat mutasi dompet digital.
2. **Melacak Transaksi**:
   - Semua mutasi saldo (debit/kredit) dapat diaudit secara real-time pada tab **Wallet Transactions**.

### Audit Logs & Monitoring Sistem
1. **Audit Logs**:
   - Setiap tindakan sensitif (membuat user, mengubah paket, menghapus NAS, top-up saldo) dicatat di menu **Audit Logs**. Anda dapat memfilter berdasarkan nama admin, jenis modul, atau rentang waktu.
2. **Monitoring Log Autentikasi**:
   - Pantau percobaan login (sukses maupun gagal) secara real-time untuk mendeteksi potensi brute force pada router pelanggan.

---

## Panduan Reseller

Reseller mengoperasikan panel dengan hak akses terbatas yang di-scope hanya untuk data miliknya sendiri. Saldo reseller akan terpotong setiap kali membuat voucher atau mengaktifkan customer postpaid.

### Manajemen Pelanggan (Customers)
Pelanggan adalah pengguna akhir (*end-user*) yang menggunakan koneksi internet (PPPoE / Hotspot).
1. **Pendaftaran Customer**:
   - Masuk ke menu **Customers** > **Add Customer**.
   - Isi username & password yang unik. Username ini yang dimasukkan di router pelanggan.
   - Pilih **Package** yang ingin digunakan.
   - Sistem otomatis membuat entri di tabel `radcheck` (username/password) dan `radusergroup` (paket layanan).
2. **Status Pelanggan**:
   - **Active**: Pelanggan dapat login dan menggunakan internet.
   - **Suspended**: Ditangguhkan manual oleh reseller (misal: karena masalah internal). Pelanggan tidak bisa login.
   - **Expired**: Masa aktif paket telah habis. Sistem otomatis memutuskan koneksi aktif pelanggan.

### Manajemen Voucher (Prepaid)
Voucher sangat cocok untuk model bisnis Hotspot/RT-RW Net prabayar.
1. **Generate Voucher Massal (Batch)**:
   - Masuk ke menu **Vouchers** > **Generate Vouchers**.
   - Pilih **Package** (menentukan harga, kecepatan, dan masa aktif voucher).
   - Masukkan jumlah voucher yang ingin dibuat (**Quantity**, misal: 50 lembar).
   - Sistem akan memotong saldo wallet Anda sebesar `Harga Paket x Jumlah Voucher`.
   - Kode voucher acak akan ter-generate otomatis.
2. **Cetak Voucher**:
   - Anda dapat mengunduh daftar voucher yang dihasilkan dalam format PDF siap cetak dengan kode QR untuk mempermudah login pengguna.
3. **Aktivasi Voucher**:
   - Ketika pelanggan memasukkan kode voucher di halaman login hotspot, status voucher di database otomatis berubah menjadi `used`, mencatat waktu pemakaian pertama, dan menghitung mundur masa aktif.

### Tagihan & Pembayaran (Postpaid)
Untuk pelanggan bulanan (biasanya PPPoE rumahan).
1. **Pembuatan Invoice**:
   - Di akhir periode penagihan, sistem otomatis meng-generate tagihan (**Invoices**) berdasarkan paket yang dipilih customer.
2. **Pencatatan Pembayaran**:
   - Pelanggan membayar secara tunai/transfer ke Reseller.
   - Reseller mencari invoice pelanggan di menu **Invoices**, lalu klik **Mark as Paid**.
   - Status pelanggan yang sempat dinonaktifkan karena telat bayar otomatis kembali aktif (*Active*).

### Monitoring Sesi Aktif & CoA (Kick User)
1. **Dashboard Monitoring**:
   - Dashboard utama menampilkan statistik live: jumlah pelanggan online, bandwidth yang sedang digunakan, dan grafik trafik.
   - Menu **Active Sessions** menampilkan detail sesi yang sedang berjalan (IP, MAC Address, lama koneksi, total volume upload/download).
2. **Memutuskan Koneksi (Kick User / CoA)**:
   - Jika ada pelanggan yang melanggar aturan atau ingin dipaksa re-autentikasi:
     - Cari username di tabel **Active Sessions**.
     - Klik tombol **Disconnect (Kick)**.
     - Radiux akan mengirimkan paket *Disconnect-Request* (CoA) UDP ke NAS tempat user tersebut terhubung, memaksa router memutuskan sesi PPPoE/Hotspot pelanggan seketika itu juga.

### Dompet Digital & Saldo Reseller
1. **Informasi Saldo**:
   - Saldo aktif reseller selalu terpampang di pojok kanan atas dashboard.
   - Jika saldo tidak mencukupi untuk biaya bulanan pelanggan postpaid atau generate voucher baru, sistem akan memblokir aksi tersebut hingga Anda melakukan top-up melalui Superadmin.
2. **Mutasi Saldo**:
   - Buka menu **My Wallet** untuk melihat daftar transaksi masuk/keluar terperinci agar pembukuan keuangan reseller tetap transparan.
