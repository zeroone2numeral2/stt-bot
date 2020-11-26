"""users names

Revision ID: 57f90fdab128
Revises: 6e8a51f3e6d8
Create Date: 2020-11-26 15:57:33.649766

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '57f90fdab128'
down_revision = '6e8a51f3e6d8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('name', sa.String))


def downgrade():
    pass
