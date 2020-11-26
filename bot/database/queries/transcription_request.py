from sqlalchemy.orm import Session
from sqlalchemy import func

from bot.database.models.transcription_request import TranscriptionRequest


def estimated_duration(session: Session, audio_length: int, threshold: int = 20):
    threshold_boundary = threshold / 2
    threshold_boundary_down = audio_length - threshold_boundary
    threshold_boundary_up = audio_length + threshold_boundary

    result = (
        session.query(func.avg(TranscriptionRequest.response_time).label('seconds'))
        .filter(TranscriptionRequest.audio_duration.between(threshold_boundary_down,  threshold_boundary_up))
        .one_or_none()
    )

    return result.seconds
