from sqlalchemy import Column, Integer, Boolean, String

from ..base import Base, engine


class TranscriptionRequest(Base):
    __tablename__ = 'transcription_requests'

    id = Column(Integer, primary_key=True)
    audio_duration = Column(Integer, default=None, nullable=True)
    sample_rate = Column(Integer, default=None, nullable=True)
    response_time = Column(Integer, default=None, nullable=True)
    success = Column(Boolean, default=None, nullable=True)

    def __init__(self, audio_duration):
        self.audio_duration = audio_duration


Base.metadata.create_all(engine)
