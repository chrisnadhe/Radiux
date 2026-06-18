"""ORM models untuk tabel inti FreeRADIUS (standar rlm_sql).

PENTING: File ini HANYA mendefinisikan ORM mapping — JANGAN ubah
skema tabel ini (nama kolom, tipe data, constraint). Tabel dibuat
via schema.sql, bukan via Alembic autogenerate (sudah di-exclude di
migrations/env.py). Lihat AGENT.md rule #1.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RadCheck(Base):
    """Atribut autentikasi & otorisasi per user."""

    __tablename__ = "radcheck"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    op: Mapped[str] = mapped_column(String(2), nullable=False, default="==")
    value: Mapped[str] = mapped_column(String(253), nullable=False, default="")

    __table_args__ = (Index("radcheck_username", "username", "attribute"),)


class RadReply(Base):
    """Atribut reply per user yang dikirim ke NAS setelah auth berhasil."""

    __tablename__ = "radreply"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    op: Mapped[str] = mapped_column(String(2), nullable=False, default="=")
    value: Mapped[str] = mapped_column(String(253), nullable=False, default="")

    __table_args__ = (Index("radreply_username", "username", "attribute"),)


class RadGroupCheck(Base):
    """Atribut check per grup/paket (diwarisi user via radusergroup)."""

    __tablename__ = "radgroupcheck"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    groupname: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    op: Mapped[str] = mapped_column(String(2), nullable=False, default="==")
    value: Mapped[str] = mapped_column(String(253), nullable=False, default="")

    __table_args__ = (Index("radgroupcheck_groupname", "groupname", "attribute"),)


class RadGroupReply(Base):
    """Atribut reply per grup/paket."""

    __tablename__ = "radgroupreply"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    groupname: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    op: Mapped[str] = mapped_column(String(2), nullable=False, default="=")
    value: Mapped[str] = mapped_column(String(253), nullable=False, default="")

    __table_args__ = (Index("radgroupreply_groupname", "groupname", "attribute"),)


class RadUserGroup(Base):
    """Mapping user ke grup/paket dengan priority."""

    __tablename__ = "radusergroup"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    groupname: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class RadAcct(Base):
    """Accounting records — sesi, durasi, byte in/out."""

    __tablename__ = "radacct"

    radacctid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    acctsessionid: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    acctuniqueid: Mapped[str] = mapped_column(String(32), nullable=False, default="", unique=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    groupname: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    realm: Mapped[str | None] = mapped_column(String(64), nullable=True, default="")
    nasipaddress: Mapped[str] = mapped_column(INET, nullable=False)
    nasportid: Mapped[str | None] = mapped_column(String(15), nullable=True)
    nasporttype: Mapped[str | None] = mapped_column(String(32), nullable=True)
    acctstarttime: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    acctupdatetime: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    acctstoptime: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    acctsessiontime: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    acctinputoctets: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    acctoutputoctets: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    calledstationid: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    callingstationid: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    acctterminatecause: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    framedipaddress: Mapped[str | None] = mapped_column(INET, nullable=True)


class RadPostAuth(Base):
    """Log percobaan autentikasi (sukses & gagal)."""

    __tablename__ = "radpostauth"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pass_: Mapped[str] = mapped_column("pass", String(64), nullable=False)
    reply: Mapped[str] = mapped_column(String(32), nullable=False)
    nasname: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    nasportid: Mapped[str] = mapped_column(String(15), nullable=False, default="")
    authdate: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="NOW()")
    class_: Mapped[str | None] = mapped_column("class", String(64), nullable=True)


class NasCore(Base):
    """Tabel NAS standar FreeRADIUS — digunakan rlm_sql untuk client lookup.

    Untuk data tambahan (vendor, tenant) gunakan NasExt di nas_ext.py.
    """

    __tablename__ = "nas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nasname: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    shortname: Mapped[str] = mapped_column(String(32), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    ports: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # CATATAN: kolom secret menyimpan shared secret TERENKRIPSI (bukan plaintext)
    # Lihat AGENT.md rule #3 dan app/core/security.py encrypt_secret()
    secret: Mapped[str] = mapped_column(String(60), nullable=False, default="secret")
    server: Mapped[str | None] = mapped_column(String(64), nullable=True)
    community: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default="RADIUS Client")
