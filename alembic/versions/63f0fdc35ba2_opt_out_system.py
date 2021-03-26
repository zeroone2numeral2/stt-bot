"""opt_out_system

Revision ID: 63f0fdc35ba2
Revises: 57f90fdab128
Create Date: 2021-03-26 16:36:50.994494

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63f0fdc35ba2'
down_revision = '57f90fdab128'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("users", column_name="tos_accepted", new_column_name="opted_out")
    op.drop_column("chats", "ignore_tos")


def downgrade():
    pass
