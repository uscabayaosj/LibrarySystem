"""Add organizationsettings.contact_note

Every error page tells the reader to "contact the library desk" and then names
no desk -- no hours, no phone, no email, no room. The instruction is only
actionable if the deployment can say who to contact, and that differs per
institution, so it belongs with the other per-deployment branding the admin
can already edit without a redeploy rather than being hardcoded.

Null on upgrade, which renders exactly the copy that shipped before this: the
error pages fall back to the generic sentence when no note is set.

Revision ID: c4d1e8b7a920
Revises: b7e2f4a91c36
Create Date: 2026-08-31 19:40:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'c4d1e8b7a920'
down_revision = 'b7e2f4a91c36'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('organization_settings',
                  sa.Column('contact_note', sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column('organization_settings', 'contact_note')
