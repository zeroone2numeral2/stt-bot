"""Added TranscriptionRequest mode

Revision ID: 2a922c119319
Revises: 84753caaa9af
Create Date: 2020-11-26 12:14:51.186715

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, Integer, Boolean, String


# revision identifiers, used by Alembic.
revision = '2a922c119319'
down_revision = '84753caaa9af'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transcription_requests",
        Column("id", Integer, primary_key=True),
        Column("audio_duration", Integer, default=None, nullable=True),
        Column("sample_rate", Integer, default=None, nullable=True),
        Column("response_time", Integer, default=None, nullable=True),
        Column("success", Boolean, default=None, nullable=True)
    )


def downgrade():
    op.drop_table("transcription_requests")
