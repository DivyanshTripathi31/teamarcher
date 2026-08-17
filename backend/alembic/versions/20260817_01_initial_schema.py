"""Initial Team Archer schema derived from the existing SQLAlchemy models.

Revision ID: 20260817_01
Revises: None
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260817_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "site_content",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_name", sa.String(length=100), nullable=False),
        sa.Column("tagline", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("objectives", sa.Text(), nullable=False),
        sa.Column("intended_users", sa.Text(), nullable=False),
        sa.Column("core_features", sa.Text(), nullable=False),
        sa.Column("roles_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "profile_avatars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("file_storage_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_storage_key"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "public_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("skills_json", sa.Text(), nullable=False),
        sa.Column("show_email_public", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "presentations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("presentation_date", sa.Date(), nullable=False),
        sa.Column("authors", sa.Text(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_storage_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_storage_key"),
        sa.UniqueConstraint("title", "version", name="uq_presentation_title_version"),
    )
    op.create_index("ix_presentations_published", "presentations", ["published"], unique=False)
    op.create_index("ix_presentations_slug", "presentations", ["slug"], unique=True)

    op.create_table(
        "presentation_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("presentation_id", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_storage_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["presentation_id"], ["presentations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_storage_key"),
    )
    op.create_index("ix_presentation_assets_presentation_id", "presentation_assets", ["presentation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_presentation_assets_presentation_id", table_name="presentation_assets")
    op.drop_table("presentation_assets")
    op.drop_index("ix_presentations_slug", table_name="presentations")
    op.drop_index("ix_presentations_published", table_name="presentations")
    op.drop_table("presentations")
    op.drop_table("public_profiles")
    op.drop_table("profile_avatars")
    op.drop_table("site_content")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
