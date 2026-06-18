import pytest
from sqlalchemy import text

from app.core.database import get_db


@pytest.mark.integration
@pytest.mark.anyio
async def test_database_connection() -> None:
    """Verifikasi koneksi database dan skema dasar berjalan di integrasi."""
    db_generator = get_db()
    try:
        db = await anext(db_generator)
        # Cek apakah kita bisa melakukan query sederhana
        result = await db.execute(text("SELECT 1"))
        assert result.scalar() == 1

        # Cek apakah tabel admin_users (dari Alembic) ada
        result = await db.execute(text("SELECT count(*) FROM admin_users"))
        assert isinstance(result.scalar(), int)

        # Cek apakah tabel radcheck (dari FreeRADIUS schema) ada
        result = await db.execute(text("SELECT count(*) FROM radcheck"))
        assert isinstance(result.scalar(), int)
    finally:
        # Panggil generator cleanup
        try:
            await anext(db_generator)
        except StopAsyncIteration:
            pass
