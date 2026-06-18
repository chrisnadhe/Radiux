"""CLI commands untuk Radiux — dijalankan via `uv run python -m app.cli`."""

import argparse
import sys


def create_superadmin() -> None:
    """Buat akun superadmin pertama secara interaktif.

    Akan diimplementasikan di Phase 1 saat model AdminUser sudah ada.
    """
    print("⚠️  Perintah ini akan diimplementasikan di Phase 1.")
    print("   Saat ini belum ada model database yang aktif.")
    sys.exit(0)


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
