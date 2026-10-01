"""add job submission metadata

Dataset name and axis labels come from the web submission form; the
matrix itself is persisted so results pages are self-contained and jobs
can be re-run server-side; progress is written by the worker while a
job runs. Nullable: jobs submitted before this revision have none.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01

"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("name", sa.String(length=200), nullable=True))
    op.add_column("jobs", sa.Column("labels", sa.JSON(), nullable=True))
    op.add_column("jobs", sa.Column("matrix", sa.JSON(), nullable=True))
    op.add_column("jobs", sa.Column("progress", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "progress")
    op.drop_column("jobs", "matrix")
    op.drop_column("jobs", "labels")
    op.drop_column("jobs", "name")
