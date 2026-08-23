"""Add user.onboarding_completed_at

Tracks whether a member has finished (or skipped) the one-time post-signup
welcome walkthrough. Null means "not shown yet"; existing accounts get null
on upgrade, which is correct -- they've already found their own way around
and should never see it retroactively (routes/member.py:welcome only redirects
new sign-ins here, not every login, once this is set).

Revision ID: b7e2f4a91c36
Revises: f3c8a1d92e47
Create Date: 2026-08-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e2f4a91c36'
down_revision = 'f3c8a1d92e47'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('onboarding_completed_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('user', 'onboarding_completed_at')
