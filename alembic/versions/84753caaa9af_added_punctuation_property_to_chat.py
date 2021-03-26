"""Added punctuation property to Chat

Revision ID: 84753caaa9af
Revises: 
Create Date: 2020-11-26 12:06:24.685003

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84753caaa9af'
down_revision = None  # no down revision: this one was the first migration script
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chats', sa.Column('punctuation', sa.Boolean))


def downgrade():
    op.drop_column('chats', 'punctuation')
