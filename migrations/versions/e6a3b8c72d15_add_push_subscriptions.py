"""Add push_subscription

Web Push mirrors each in-app notice to the member's subscribed devices and
drives the installed app's icon badge. A subscription is one device's
endpoint plus its encryption keys; the endpoint is unique so a device that
re-subscribes as a different member moves rather than duplicates.

Revision ID: e6a3b8c72d15
Revises: d5f2c9a41b83
Create Date: 2026-09-02 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'e6a3b8c72d15'
down_revision = 'd5f2c9a41b83'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'push_subscription',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('p256dh', sa.String(length=200), nullable=False),
        sa.Column('auth', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('endpoint', name='uq_push_subscription_endpoint'),
    )
    op.create_index('ix_push_subscription_user_id', 'push_subscription', ['user_id'])


def downgrade():
    op.drop_index('ix_push_subscription_user_id', table_name='push_subscription')
    op.drop_table('push_subscription')
