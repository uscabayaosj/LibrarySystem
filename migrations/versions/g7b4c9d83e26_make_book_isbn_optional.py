"""Allow books without an ISBN while retaining uniqueness for supplied ISBNs.

Revision ID: g7b4c9d83e26
Revises: e6a3b8c72d15
"""
from alembic import op
import sqlalchemy as sa


revision = 'g7b4c9d83e26'
down_revision = 'e6a3b8c72d15'
branch_labels = None
depends_on = None


def upgrade():
    # NULL allows multiple uncatalogued ISBNs under the existing unique index
    # on both SQLite and Postgres; an empty string would allow only one.
    with op.batch_alter_table('book') as batch_op:
        batch_op.alter_column('isbn', existing_type=sa.String(length=13),
                              existing_nullable=False, nullable=True)
    op.execute(sa.text("UPDATE book SET isbn = NULL WHERE TRIM(isbn) = ''"))


def downgrade():
    # Restoring NOT NULL requires real ISBNs first. Never delete books or
    # invent identifiers just to make a rollback succeed.
    missing = op.get_bind().execute(sa.text(
        'SELECT COUNT(*) FROM book WHERE isbn IS NULL'
    )).scalar_one()
    if missing:
        raise RuntimeError('Assign ISBNs to all books before downgrading this migration.')
    with op.batch_alter_table('book') as batch_op:
        batch_op.alter_column('isbn', existing_type=sa.String(length=13),
                              existing_nullable=True, nullable=False)
