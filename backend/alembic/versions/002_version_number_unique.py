"""Add unique constraint on resume version numbers per resume."""

from __future__ import annotations

from alembic import op

revision = "002_version_number_unique"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_resume_versions_resume_id_version_number",
        "resume_versions",
        ["resume_id", "version_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_resume_versions_resume_id_version_number",
        "resume_versions",
        type_="unique",
    )
