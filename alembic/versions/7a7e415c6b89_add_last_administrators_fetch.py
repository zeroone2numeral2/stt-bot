"""add last_administrators_fetch

Revision ID: 7a7e415c6b89
Revises: 63f0fdc35ba2
Create Date: 2021-03-27 02:48:25.394158

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a7e415c6b89'
down_revision = '63f0fdc35ba2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chats', sa.Column('last_administrators_fetch', sa.DateTime(timezone=True)))


def downgrade():
    pass
