"""Resize pgvector columns for Groq nomic-embed-text-v1_5 (768 dims).

Revision ID: 004_groq_embedding_dimensions
Revises: 003_ai_input_hash_service_index
Create Date: 2026-08-25
"""

from typing import Sequence, Union

from alembic import op

revision: str = "004_groq_embedding_dimensions"
down_revision: Union[str, Sequence[str], None] = "003_ai_input_hash_service_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_DIM = 768
OLD_DIM = 1536


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_resumes_content_embedding")
    op.execute("DROP INDEX IF EXISTS ix_resume_versions_content_embedding")
    op.execute("DROP INDEX IF EXISTS ix_job_descriptions_content_embedding")

    op.execute("ALTER TABLE resumes ALTER COLUMN content_embedding TYPE vector USING NULL")
    op.execute(f"ALTER TABLE resumes ALTER COLUMN content_embedding TYPE vector({NEW_DIM})")
    op.execute("ALTER TABLE resume_versions ALTER COLUMN content_embedding TYPE vector USING NULL")
    op.execute(f"ALTER TABLE resume_versions ALTER COLUMN content_embedding TYPE vector({NEW_DIM})")
    op.execute("ALTER TABLE job_descriptions ALTER COLUMN content_embedding TYPE vector USING NULL")
    op.execute(
        f"ALTER TABLE job_descriptions ALTER COLUMN content_embedding TYPE vector({NEW_DIM})"
    )

    op.execute(
        "CREATE INDEX ix_resumes_content_embedding ON resumes "
        "USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX ix_resume_versions_content_embedding ON resume_versions "
        "USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX ix_job_descriptions_content_embedding ON job_descriptions "
        "USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_resumes_content_embedding")
    op.execute("DROP INDEX IF EXISTS ix_resume_versions_content_embedding")
    op.execute("DROP INDEX IF EXISTS ix_job_descriptions_content_embedding")

    op.execute("ALTER TABLE resumes ALTER COLUMN content_embedding TYPE vector USING NULL")
    op.execute(f"ALTER TABLE resumes ALTER COLUMN content_embedding TYPE vector({OLD_DIM})")
    op.execute("ALTER TABLE resume_versions ALTER COLUMN content_embedding TYPE vector USING NULL")
    op.execute(f"ALTER TABLE resume_versions ALTER COLUMN content_embedding TYPE vector({OLD_DIM})")
    op.execute("ALTER TABLE job_descriptions ALTER COLUMN content_embedding TYPE vector USING NULL")
    op.execute(
        f"ALTER TABLE job_descriptions ALTER COLUMN content_embedding TYPE vector({OLD_DIM})"
    )
