"""composite index for AI cache lookups

Revision ID: 003_ai_input_hash_service_index
Revises: 002_version_number_unique
Create Date: 2026-08-25
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_ai_input_hash_service_index"
down_revision: Union[str, Sequence[str], None] = "002_version_number_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_ai_analysis_results_input_hash_service_name",
        "ai_analysis_results",
        ["input_hash", "service_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_analysis_results_input_hash_service_name",
        table_name="ai_analysis_results",
    )
