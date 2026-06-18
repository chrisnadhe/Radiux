"""seed default tenant

Revision ID: c0cf4fd5f4ac
Revises: a64cd5ec2f32
Create Date: 2026-06-18 13:23:19.628714+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0cf4fd5f4ac'
down_revision: Union[str, None] = 'a64cd5ec2f32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.execute(
        "INSERT INTO tenants (id, name, slug, status, is_active, created_at, updated_at) "
        "VALUES (1, 'Main ISP', 'main-isp', 'active', true, NOW(), NOW()) "
        "ON CONFLICT DO NOTHING;"
    )

def downgrade() -> None:
    """Rollback migration."""
    op.execute("DELETE FROM tenants WHERE id = 1;")
