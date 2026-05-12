"""Add fcm_token and language to fax_jobs

Revision ID: 0002_add_fcm_fields
Revises: 0001_initial
Create Date: 2026-05-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_add_fcm_fields'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("fax_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("fcm_token", sa.String(512), nullable=True)
        )
        batch_op.add_column(
            sa.Column("language", sa.String(10), nullable=True, server_default="en")
        )


def downgrade() -> None:
    with op.batch_alter_table("fax_jobs") as batch_op:
        batch_op.drop_column("language")
        batch_op.drop_column("fcm_token")

