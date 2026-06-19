"""Unit tests untuk audit_service — log_action."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import audit_service


def _make_db() -> AsyncMock:
    """Buat mock AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.unit
class TestAuditServiceLogAction:
    """Test suite untuk audit_service.log_action()."""

    async def test_log_action_returns_audit_log(self) -> None:
        """log_action harus mengembalikan objek AuditLog."""
        db = _make_db()
        await audit_service.log_action(db, action="LOGIN_SUCCESS", user_id=1)
        # Pastikan db.add dipanggil
        db.add.assert_called_once()
        # Pastikan commit dipanggil
        db.commit.assert_awaited_once()
        # Pastikan refresh dipanggil
        db.refresh.assert_awaited_once()

    async def test_log_action_with_all_fields(self) -> None:
        """log_action harus meneruskan semua field ke AuditLog."""
        from app.models.audit_logs import AuditLog

        db = _make_db()
        await audit_service.log_action(
            db,
            action="CREATE_CUSTOMER",
            user_id=42,
            table_name="customers",
            record_id=99,
            details={"name": "Budi"},
            ip_address="192.168.1.1",
        )
        # Ambil objek AuditLog yang di-pass ke db.add
        added_obj: AuditLog = db.add.call_args[0][0]
        assert isinstance(added_obj, AuditLog)
        assert added_obj.action == "CREATE_CUSTOMER"
        assert added_obj.user_id == 42
        assert added_obj.table_name == "customers"
        assert added_obj.record_id == "99"  # di-cast ke str
        assert added_obj.details == {"name": "Budi"}
        assert added_obj.ip_address == "192.168.1.1"

    async def test_log_action_record_id_cast_to_str(self) -> None:
        """record_id int harus di-cast ke str sebelum disimpan."""
        from app.models.audit_logs import AuditLog

        db = _make_db()
        await audit_service.log_action(db, action="DELETE_NAS", record_id=7)
        added_obj: AuditLog = db.add.call_args[0][0]
        assert added_obj.record_id == "7"

    async def test_log_action_none_details_defaults_to_empty_dict(self) -> None:
        """Jika details=None, harus default ke dict kosong."""
        from app.models.audit_logs import AuditLog

        db = _make_db()
        await audit_service.log_action(db, action="LOGIN_FAILED")
        added_obj: AuditLog = db.add.call_args[0][0]
        assert added_obj.details == {}

    async def test_log_action_without_optional_fields(self) -> None:
        """log_action dengan hanya action (tanpa field opsional) harus berhasil."""
        db = _make_db()
        await audit_service.log_action(db, action="SYSTEM_START")
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
