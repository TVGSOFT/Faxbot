"""Add from_number to fax_jobs

Revision ID: 0003_add_from_number
Revises: 0002_add_fcm_fields
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_add_from_number'
down_revision = '0002_add_fcm_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("fax_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("from_number", sa.String(64), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("fax_jobs") as batch_op:
        batch_op.drop_column("from_number")
