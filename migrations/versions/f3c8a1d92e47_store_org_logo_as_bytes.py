"""Store the organization logo as bytes instead of a filename on disk

Replaces organization_settings.logo_filename (a pointer to a file that had
to live on a persistent, writable disk alongside the app process) with the
logo's own bytes. See branding_images.py's module docstring for why: this
app has now hit two hosts where "the app process has a persistent disk"
doesn't hold -- a Render disk declared incompatible with its own plan, and
Vercel's serverless functions, which have none at all, on any plan. A
database column has no such dependency.

Revision ID: f3c8a1d92e47
Revises: a062ad0fb313
Create Date: 2026-08-19 00:00:00.000000
"""
import os
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = 'f3c8a1d92e47'
down_revision = 'a062ad0fb313'
branch_labels = None
depends_on = None

_CONTENT_TYPE_FOR_EXT = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'webp': 'image/webp',
}


def upgrade():
    op.add_column('organization_settings', sa.Column('logo_data', sa.LargeBinary(), nullable=True))
    op.add_column('organization_settings', sa.Column('logo_content_type', sa.String(length=32), nullable=True))
    op.add_column('organization_settings', sa.Column('logo_updated_at', sa.DateTime(), nullable=True))

    # Best-effort data carry-over: if this migration is being run on a host
    # that still has the old static/uploads/branding/logo.<ext> file sitting
    # next to it (e.g. locally, before decommissioning an old disk-based
    # deployment), read it into the new column instead of silently dropping
    # it. Never required for the migration to succeed -- any error here is
    # swallowed, because a stale, unreadable, or absent file is the expected
    # case on a fresh install or a host that never had a disk in the first
    # place (Vercel), not a failure.
    try:
        conn = op.get_bind()
        row = conn.execute(sa.text(
            'SELECT id, logo_filename FROM organization_settings WHERE logo_filename IS NOT NULL'
        )).fetchone()
        if row is not None:
            row_id, filename = row
            ext = filename.rsplit('.', 1)[-1].lower()
            path = os.path.join('static', 'uploads', 'branding', filename)
            with open(path, 'rb') as f:
                data = f.read()
            conn.execute(
                sa.text(
                    'UPDATE organization_settings '
                    'SET logo_data = :data, logo_content_type = :ct, logo_updated_at = :ts '
                    'WHERE id = :id'
                ),
                {'data': data, 'ct': _CONTENT_TYPE_FOR_EXT.get(ext, 'image/png'),
                 'ts': datetime.utcnow(), 'id': row_id},
            )
    except Exception:
        pass

    op.drop_column('organization_settings', 'logo_filename')


def downgrade():
    op.add_column('organization_settings', sa.Column('logo_filename', sa.String(length=120), nullable=True))
    op.drop_column('organization_settings', 'logo_updated_at')
    op.drop_column('organization_settings', 'logo_content_type')
    op.drop_column('organization_settings', 'logo_data')
