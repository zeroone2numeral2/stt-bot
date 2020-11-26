"""Second attempt: added punctuation property to Chat

Revision ID: 7487407ac290
Revises: 4686e87041c6
Create Date: 2020-11-26 10:49:13.783916

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7487407ac290'
down_revision = '4686e87041c6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chats', sa.Column('punctuation', sa.Boolean))


def downgrade():
    pass
