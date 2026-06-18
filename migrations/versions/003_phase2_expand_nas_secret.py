"""expand nas secret column

Revision ID: a64cd5ec2f32
Revises: 002_phase2_vendor_profiles
Create Date: 2026-06-18 13:04:08.177215+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a64cd5ec2f32'
down_revision: Union[str, None] = '002_phase2_vendor_profiles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.alter_column(
        'nas',
        'secret',
        type_=sa.String(length=255),
        existing_type=sa.String(length=60),
        existing_nullable=False
    )


def downgrade() -> None:
    """Rollback migration."""
    op.alter_column(
        'nas',
        'secret',
        type_=sa.String(length=60),
        existing_type=sa.String(length=255),
        existing_nullable=False
    )
