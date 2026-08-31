"""Add desk-issued password reset codes, and the notification table

Two features that share a migration because they arrived together.

user.reset_code_hash / reset_expires_at
    A librarian-issued, single-use password reset. Only the hash is stored, so
    a database dump cannot be replayed into account access; the plaintext code
    exists for exactly one HTTP response. Nullable, so every existing account
    upgrades to "no reset outstanding", which is correct.

notification
    In-app notices (hold ready, due soon, overdue, checked out at the desk).
    The (user_id, dedupe_key) unique constraint is what makes generation
    idempotent: the librarian's circulation sweep can run five times a day
    without a member collecting five copies of the same "due in 2 days".

Revision ID: d5f2c9a41b83
Revises: c4d1e8b7a920
Create Date: 2026-08-31 20:15:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'd5f2c9a41b83'
down_revision = 'c4d1e8b7a920'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch:
        batch.add_column(sa.Column('reset_code_hash', sa.String(length=255), nullable=True))
        batch.add_column(sa.Column('reset_expires_at', sa.DateTime(), nullable=True))

    op.create_table(
        'notification',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('body', sa.String(length=400), nullable=True),
        sa.Column('link_endpoint', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('dedupe_key', sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'dedupe_key', name='uq_notification_user_dedupe'),
    )
    op.create_index('ix_notification_user_id', 'notification', ['user_id'])
    op.create_index('ix_notification_created_at', 'notification', ['created_at'])


def downgrade():
    op.drop_index('ix_notification_created_at', table_name='notification')
    op.drop_index('ix_notification_user_id', table_name='notification')
    op.drop_table('notification')
    with op.batch_alter_table('user') as batch:
        batch.drop_column('reset_expires_at')
        batch.drop_column('reset_code_hash')
