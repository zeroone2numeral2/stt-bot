import datetime
import logging
from typing import Tuple, Union

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram import Update, Message

from bot.database.models.chat import Chat
from bot.database.models.user import User
from bot.database.models.transcription_request import TranscriptionRequest
from bot.database.queries import transcription_request
from google.speechtotext import VoiceMessageLocal
from google.speechtotext import VoiceMessageRemote
from google.speechtotext.exceptions import UnsupportedFormat
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)


def recognize_voice(
        voice: [VoiceMessageLocal, VoiceMessageRemote],
        update: Update,
        session: Session,
        punctuation: [bool, None] = None,
) -> Tuple[Message, Union[str, None]]:
    if punctuation is None:
        punctuation = config.google.punctuation

    if voice.short:
        text = "<i>Inizio trascrizione...</i>"
    else:
        avg_response_time = transcription_request.estimated_duration(session, voice.duration)
        text = "<i>Inizio trascrizione... Per i vocali >1 minuto potrebbe volerci un po' di più</i>"
        if avg_response_time:
            text = text.replace("</i>", f" (stimato: {round(avg_response_time, 1)}\")</i>")

    message_to_edit = update.message.reply_html(text, disable_notification=True, quote=True)

    start = datetime.datetime.now()

    request = TranscriptionRequest(audio_duration=voice.duration)

    try:
        raw_transcript, confidence = voice.recognize(punctuation=punctuation)
    except UnsupportedFormat:
        logger.error("unsupported format while transcribing voice %s", voice.file_path)
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        return message_to_edit, None
    except Exception as e:
        logger.error("unknown exception while transcribing voice %s: ", voice.file_path, str(e))
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        return message_to_edit, None

    end = datetime.datetime.now()
    elapsed = round((end - start).total_seconds(), 1)

    if not raw_transcript:
        logger.warning("request for voice message \"%s\" returned empty response (file not deleted)", voice.file_path)
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        return message_to_edit, None

    request.successful(elapsed, sample_rate=voice.sample_rate)
    session.add(request)  # add the request instance to the session only on success

    # print('\n'.join([f"{round(a.confidence, 2)}: {a.transcript}" for a in result]))

    transcription = f"\"<i>{raw_transcript}</i>\" <b>[{confidence} {elapsed}\"]</b>"

    if config.misc.remove_downloaded_files:
        voice.cleanup()

    return message_to_edit, transcription


def ignore_message_group(
        session: Session,
        user: User,
        chat: Chat,
        message: Message
):
    its_ok_because = "sender accepted tos"
    is_forward_from_user = utilities.is_forward_from_user(message)
    if chat.ignore_tos:
        logger.info("chat %d is set to ignore tos: we can transcribe the audio", message.chat.id)
        its_ok_because = "chat is set to ignore tos"
    elif not is_forward_from_user and not user.tos_accepted:
        logger.info("not forward and sender did not accept tos: ignoring voice message")
        return True, "sender did not accept tos"
    elif is_forward_from_user and utilities.user_hidden_account(message):
        logger.info("forwarded message (original sender with hidden account): we can transcribe the audio")
        its_ok_because = "forwarded message: original sender with hidden account"
    elif is_forward_from_user and message.forward_from.is_bot:
        logger.info("forwarded from bot: we can transcribe the audio")
        its_ok_because = "forwarded message: original is a bot"
    elif is_forward_from_user:
        # forwarded message from an user who did not decide to hide their account
        user: [User, None] = session.query(User).filter(User.user_id == message.forward_from.id).one_or_none()
        if not user or not user.tos_accepted:
            logger.info("forwarded message: no user in db, or user did not accept tos: ignoring voice message")
            return True, "forward from user: user not in db or did not accept tos"
        else:
            its_ok_because = "forwarded message: user accepted tos"

    return False, its_ok_because
