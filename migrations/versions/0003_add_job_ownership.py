"""add job ownership

Existing jobs predate API keys and have no owner; the service is
pre-release, so they are dropped rather than given a nullable owner.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17

"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM jobs")
    op.add_column("jobs", sa.Column("api_key_id", sa.String(36), nullable=False))
    op.create_foreign_key("fk_jobs_api_key_id", "jobs", "api_keys", ["api_key_id"], ["id"])
    op.create_index("ix_jobs_api_key_id", "jobs", ["api_key_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_api_key_id", table_name="jobs")
    op.drop_constraint("fk_jobs_api_key_id", "jobs", type_="foreignkey")
    op.drop_column("jobs", "api_key_id")
