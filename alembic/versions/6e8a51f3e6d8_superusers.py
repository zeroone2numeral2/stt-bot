"""superusers

Revision ID: 6e8a51f3e6d8
Revises: 2a922c119319
Create Date: 2020-11-26 15:21:45.201560

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e8a51f3e6d8'
down_revision = '2a922c119319'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('superuser', sa.Boolean))
    op.drop_column('users', 'whitelisted_forwards')
    op.drop_column('users', 'can_add_to_groups')


def downgrade():
    pass
