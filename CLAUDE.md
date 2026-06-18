# CLAUDE.md

Seluruh aturan proyek Radiux (stack, konvensi kode, batasan arsitektur, dan **Kebijakan Perubahan Besar**) ada di [`AGENTS.md`](./AGENTS.md) di root repo ini.

Baca dan ikuti `AGENTS.md` sepenuhnya sebelum membuat perubahan apa pun di codebase ini. File ini sengaja dibuat singkat agar tidak ada dua versi aturan yang bisa berbeda — jangan tambahkan aturan baru di sini, tambahkan di `AGENTS.md`.

Poin yang paling penting untuk diingat di setiap sesi: **jangan lakukan perubahan besar (skema database, refactor multi-file, dependency mayor, logic auth/RBAC, konfigurasi deployment, atau keputusan arsitektur di PLAN.md) tanpa konfirmasi eksplisit dari pengguna terlebih dahulu.** Detail lengkap kategori dan prosedurnya ada di `AGENTS.md` bagian "Kebijakan Perubahan Besar".
