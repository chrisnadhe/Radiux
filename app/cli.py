"""CLI commands untuk Radiux — dijalankan via `uv run python -m app.cli`."""

import argparse
import asyncio
import getpass
import sys


async def async_create_superadmin() -> None:
    """Fungsi internal async untuk membuat superadmin."""
    print("=== Membuat Akun Superadmin Radiux ===")
    try:
        username = input("Username: ").strip()
        if not username:
            print("❌ Username tidak boleh kosong.")
            sys.exit(1)

        email = input("Email: ").strip()
        if not email:
            print("❌ Email tidak boleh kosong.")
            sys.exit(1)

        password = getpass.getpass("Password: ")
        if not password:
            print("❌ Password tidak boleh kosong.")
            sys.exit(1)

        password_confirm = getpass.getpass("Konfirmasi Password: ")
        if password != password_confirm:
            print("❌ Password tidak cocok.")
            sys.exit(1)

        full_name = input("Nama Lengkap (opsional): ").strip() or None

        from app.core.database import AsyncSessionLocal
        from app.services.auth_service import create_superadmin as create_superadmin_service

        async with AsyncSessionLocal() as db:
            user = await create_superadmin_service(
                db=db,
                username=username,
                email=email,
                password=password,
                full_name=full_name,
            )
            await db.commit()
            print(f"✅ Akun superadmin '{user.username}' berhasil dibuat!")
    except Exception as e:
        print(f"❌ Gagal membuat superadmin: {e}")
        sys.exit(1)


def create_superadmin() -> None:
    """Buat akun superadmin pertama secara interaktif."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(async_create_superadmin())


def main() -> None:
    """Entry point untuk CLI Radiux."""
    parser = argparse.ArgumentParser(
        prog="radiux",
        description="Radiux CLI — tools untuk administrasi aplikasi",
    )
    subparsers = parser.add_subparsers(dest="command", help="Perintah yang tersedia")

    # create-superadmin
    subparsers.add_parser(
        "create-superadmin",
        help="Buat akun superadmin pertama",
    )

    args = parser.parse_args()

    if args.command == "create-superadmin":
        create_superadmin()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
