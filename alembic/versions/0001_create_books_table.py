"""crear tabla books

Revision ID: 0001
Revises:
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("isbn", sa.String(length=20), nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 2), nullable=False),
        sa.Column("selling_price_local", sa.Numeric(12, 2), nullable=True),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("supplier_country", sa.String(length=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("isbn", name="uq_books_isbn"),
    )
    op.create_index("ix_books_isbn", "books", ["isbn"])
    op.create_index("ix_books_category", "books", ["category"])


def downgrade() -> None:
    op.drop_index("ix_books_category", table_name="books")
    op.drop_index("ix_books_isbn", table_name="books")
    op.drop_table("books")
