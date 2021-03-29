from .models.chat import Chat
from .models.user import User
from .models.transcription_request import TranscriptionRequest
from .models.chat_administrator import ChatAdministrator
from .models.message_to_delete import MessageToDelete
from .base import Base, engine

Base.metadata.create_all(engine)
