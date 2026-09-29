"""add job matrix dimensions

Matrix shape is recorded on the job row so analytics can aggregate runtime
by input size without unpacking JSON. Nullable: jobs submitted before this
revision have no recorded shape.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-29

"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("n_mutation_types", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("n_samples", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "n_samples")
    op.drop_column("jobs", "n_mutation_types")
