"""Model Notification — log notifikasi yang dikirim ke pelanggan/admin/reseller."""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationChannel(enum.StrEnum):
    """Kanal pengiriman notifikasi.

    Desain pluggable: tambah channel baru (EMAIL, WHATSAPP) di sini
    tanpa mengubah model atau service core — cukup implementasikan
    handler baru di notification_service.py.
    """

    TELEGRAM = "telegram"
    EMAIL = "email"  # belum aktif — siap untuk implementasi mendatang
    WHATSAPP = "whatsapp"  # belum aktif — siap untuk implementasi mendatang


class NotificationEventType(enum.StrEnum):
    """Jenis event yang memicu notifikasi."""

    EXPIRY_WARNING = "expiry_warning"  # customer akan expired dalam N hari
    LOW_BALANCE = "low_balance"  # saldo reseller menipis
    NAS_DOWN = "nas_down"  # NAS offline > threshold
    TEST = "test"  # tes manual dari UI/API


class NotificationStatus(enum.StrEnum):
    """Status pengiriman notifikasi."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"  # channel tidak dikonfigurasi, diabaikan


class Notification(Base):
    """Log notifikasi yang dikirim sistem Radiux.

    Setiap record mewakili satu upaya pengiriman notifikasi ke satu channel.
    Jika satu event dikirim ke 2 channel berbeda, akan ada 2 record.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Penerima
    recipient_type: Mapped[str] = mapped_column(String(32), nullable=False)  # customer/tenant/admin
    recipient_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # ID sesuai recipient_type

    # Channel & event
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        Enum(
            NotificationEventType,
            name="notification_event_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )

    # Konten
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Status pengiriman
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(
            NotificationStatus,
            name="notification_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tenant scope (opsional — None = notifikasi global/sistem)
    tenant_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Notification id={self.id} channel={self.channel} event={self.event_type} status={self.status}>"
