# GEMINI.md

Seluruh aturan proyek Radiux (stack, konvensi kode, batasan arsitektur, dan **Kebijakan Perubahan Besar**) ada di [`AGENTS.md`](./AGENTS.md) di root repo ini.

Baca dan ikuti `AGENTS.md` sepenuhnya sebelum membuat perubahan apa pun di codebase ini. Jangan tambahkan aturan baru di sini — tambahkan di `AGENTS.md` agar semua tool/model tetap konsisten.

Poin penting: **jangan lakukan perubahan besar (skema database, refactor multi-file, dependency mayor, logic auth/RBAC, konfigurasi deployment, atau keputusan arsitektur di PLAN.md) tanpa konfirmasi eksplisit dari pengguna terlebih dahulu.**

> Catatan untuk Google Antigravity: file ini punya prioritas lebih tinggi dari `AGENTS.md` jika ada konflik. File ini sengaja dibuat kosong/pointer saja — JANGAN tambahkan rule Antigravity-spesifik di sini kecuali benar-benar perlu override, karena itu akan membuat perilaku Antigravity berbeda dari tool lain yang membaca `AGENTS.md`. Untuk rule tambahan khusus workspace, gunakan `.agent/rules/` alih-alih menulis di sini.
