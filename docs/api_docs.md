# Dokumentasi API Radiux

Aplikasi Radiux menyediakan API RESTful untuk integrasi sistem eksternal (seperti payment gateway, aplikasi CRM, atau portal pelanggan mandiri). Seluruh endpoint utama berada di bawah prefix `/api/v1`.

---

## Daftar Isi
1. [Mekanisme Autentikasi JWT](#mekanisme-autentikasi-jwt)
2. [Prinsip Scoping Multi-Tenant](#prinsip-scoping-multi-tenant)
3. [Rate Limiting & Penanganan Error](#rate-limiting--penanganan-error)
4. [Contoh Integrasi Kode](#contoh-integrasi-kode)

---

## Mekanisme Autentikasi JWT

Seluruh request API Radiux yang bersifat privat dilindungi menggunakan JWT (JSON Web Token) dengan metode **Bearer Token**.

### 1. Meminta Token Akses (Login)
Untuk mendapatkan token, kirim request `POST` dengan tipe data `application/x-www-form-urlencoded` ke endpoint `/api/v1/auth/token`.

*   **Endpoint**: `POST /api/v1/auth/token`
*   **Payload**:
    *   `username` (string, wajib)
    *   `password` (string, wajib)

#### Response Sukses (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Mengirimkan Token pada Request
Sertakan token yang didapatkan ke dalam header HTTP `Authorization` pada setiap request API selanjutnya:
```http
Authorization: Bearer <access_token>
```

---

## Prinsip Scoping Multi-Tenant

Sistem Radiux dirancang aman dari kebocoran data antar reseller (*data leakage*) melalui mekanisme isolasi data tingkat query database.

### Logika Scoping Berdasarkan Role:
1.  **Superadmin**:
    *   Secara default dapat melihat seluruh data dari semua tenant/reseller.
    *   Dapat memfilter data spesifik milik tenant tertentu dengan mengirimkan parameter query `tenant_id` (contoh: `/api/v1/customers?tenant_id=5`).
2.  **Reseller**:
    *   Sistem secara otomatis mengidentifikasi identitas reseller dari JWT payload.
    *   Semua query database (Customers, Packages, Vouchers, Invoices, Payments) akan disaring menggunakan operator `WHERE tenant_id = :reseller_tenant_id`.
    *   Upaya mengirimkan query parameter `tenant_id` milik reseller lain akan **diabaikan sepenuhnya** oleh sistem. Reseller hanya dapat melihat dan memodifikasi objek di dalam batas tenant mereka sendiri.

---

## Rate Limiting & Penanganan Error

Untuk mencegah serangan DoS (*Denial of Service*) dan penyalahgunaan API, Radiux membatasi jumlah request pada endpoint tertentu (seperti `/api/v1/auth/token`) menggunakan Redis Rate Limiter.

### Batasan Default:
*   Jika batas frekuensi terlampaui, API akan mengembalikan kode status **HTTP 429 Too Many Requests**.

### Kode Status & Respons Error Standar:

*   **400 Bad Request**: Request tidak valid atau tidak memenuhi prasyarat logika bisnis.
    ```json
    { "detail": "Saldo wallet tidak mencukupi untuk melakukan transaksi ini." }
    ```
*   **401 Unauthorized**: Token JWT tidak valid, tidak disertakan, atau sudah kedaluwarsa.
    ```json
    { "detail": "Could not validate credentials" }
    ```
*   **403 Forbidden**: Akun Anda tidak memiliki hak akses yang cukup untuk menjalankan aksi ini.
    ```json
    { "detail": "Not enough permissions" }
    ```
*   **404 Not Found**: Data yang dicari tidak ditemukan atau milik tenant/reseller lain.
    ```json
    { "detail": "Customer not found" }
    ```
*   **422 Unprocessable Entity**: Format payload JSON salah atau skema Pydantic tidak terpenuhi.
    ```json
    {
      "detail": [
        {
          "loc": ["body", "email"],
          "msg": "value is not a valid email address",
          "type": "value_error.email"
        }
      ]
    }
    ```

---

## Contoh Integrasi Kode

Berikut adalah contoh cara berinteraksi dengan API Radiux untuk beberapa skenario umum menggunakan `curl` dan pustaka `requests` Python.

### 1. Autentikasi / Login (Mendapatkan Token)

#### Menggunakan cURL:
```bash
curl -X POST "https://localhost/api/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin_reseller&password=secretpassword" \
     --insecure
```

#### Menggunakan Python:
```python
import requests

url = "https://localhost/api/v1/auth/token"
payload = {
    "username": "admin_reseller",
    "password": "secretpassword"
}

# verify=False digunakan jika masih menggunakan sertifikat SSL self-signed
response = requests.post(url, data=payload, verify=False)
token_data = response.json()
access_token = token_data["access_token"]
print("Token Akses:", access_token)
```

---

### 2. Membuat Pelanggan Baru

#### Menggunakan cURL:
```bash
curl -X POST "https://localhost/api/v1/customers" \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "customer_pppoe_1",
       "password": "password_pelanggan",
       "package_id": 2,
       "full_name": "Budi Santoso",
       "email": "budi@example.com",
       "phone": "081234567890"
     }' \
     --insecure
```

#### Menggunakan Python:
```python
import requests

url = "https://localhost/api/v1/customers"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
payload = {
    "username": "customer_pppoe_1",
    "password": "password_pelanggan",
    "package_id": 2,
    "full_name": "Budi Santoso",
    "email": "budi@example.com",
    "phone": "081234567890"
}

response = requests.post(url, json=payload, headers=headers, verify=False)
print("Response:", response.status_code, response.json())
```

---

### 3. Memutus Sesi Pengguna Aktif (CoA Disconnect / Kick)
Digunakan untuk memutuskan koneksi aktif router client PPPoE/Hotspot secara paksa dari sistem eksternal.

#### Menggunakan cURL:
```bash
curl -X POST "https://localhost/api/v1/sessions/kick" \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "customer_pppoe_1"
     }' \
     --insecure
```

#### Menggunakan Python:
```python
import requests

url = "https://localhost/api/v1/sessions/kick"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
payload = {
    "username": "customer_pppoe_1"
}

response = requests.post(url, json=payload, headers=headers, verify=False)
print("Response:", response.status_code, response.json())
# Output sukses: 200 OK dengan {"status": "success", "message": "Disconnect-Request sent successfully"}
```
