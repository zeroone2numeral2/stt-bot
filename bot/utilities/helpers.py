import datetime
import logging
from typing import Tuple, Union

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram import Update, Message, MAX_MESSAGE_LENGTH, ParseMode

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


class RecogResult:
    def __int__(self, message_to_edit=None, raw_transcript=None, confidence=None, elapsed=None, transcription=None):
        self.message_to_edit: [Message, None] = message_to_edit
        self.raw_transcript: [str, None] = raw_transcript
        self.confidence: [float, None] = confidence
        self.elapsed: [float, None] = elapsed
        self.transcription: [str, None] = transcription


def recognize_voice(
        voice: [VoiceMessageLocal, VoiceMessageRemote],
        update: Update,
        session: Session,
        punctuation: [bool, None] = None,
) -> RecogResult:
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

    result = RecogResult(message_to_edit)

    start = datetime.datetime.now()

    request = TranscriptionRequest(audio_duration=voice.duration)

    try:
        raw_transcript, confidence = voice.recognize(punctuation=punctuation)
    except UnsupportedFormat:
        logger.error("unsupported format while transcribing voice %s", voice.file_path)
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        # return result
        return message_to_edit, None
    except Exception as e:
        logger.error("unknown exception while transcribing voice %s: ", voice.file_path, str(e))
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        # return result
        return message_to_edit, None

    result.raw_transcript = raw_transcript
    result.confidence = confidence

    end = datetime.datetime.now()
    elapsed = round((end - start).total_seconds(), 1)
    result.elapsed = elapsed

    if not raw_transcript:
        logger.warning("request for voice message \"%s\" returned empty response (file not deleted)", voice.file_path)
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        # return result
        return message_to_edit, None

    request.successful(elapsed, sample_rate=voice.sample_rate)
    session.add(request)  # add the request instance to the session only on success

    # print('\n'.join([f"{round(a.confidence, 2)}: {a.transcript}" for a in result]))

    transcription = f"\"<i>{raw_transcript}</i>\" <b>[{confidence} {elapsed}\"]</b>"
    result.transcription = transcription

    if config.misc.remove_downloaded_files:
        voice.cleanup()

    # return result
    return message_to_edit, transcription


def ignore_message_group(
        session: Session,
        user: User,
        chat: Chat,
        message: Message
):
    is_forward_from_user = utilities.is_forward_from_user(message)
    if chat.ignore_tos:
        return False, "chat is set to ignore tos"
    elif not is_forward_from_user and not user.tos_accepted:
        return True, "non-forwarded and sender did not accept tos"
    elif is_forward_from_user and utilities.user_hidden_account(message):
        return False, "forwarded message: original sender with hidden account"
    elif is_forward_from_user and message.forward_from.is_bot:
        return False, "forwarded message: original sender is a bot"
    elif is_forward_from_user:
        # forwarded message from an user who did not decide to hide their account
        user: [User, None] = session.query(User).filter(User.user_id == message.forward_from.id).one_or_none()
        if not user or not user.tos_accepted:
            return True, "forwarded message: original sender not in db or did not accept tos"
        else:
            return False, "forwarded message: original sender accepted tos"

    return False, "sender accepted tos"


def send_transcription(result: RecogResult) -> int:
    if len(result.transcription) < MAX_MESSAGE_LENGTH:
        result.message_to_edit.edit_text(
            result.transcription,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )
        return 1

    # 1: build the messages to send
    texts = []
    candidate_text = ''
    start_message_by = '<i>"'
    end_message_by = '</i>" <b>[{}/{}]</b>'
    additional_characters = len(start_message_by) + len(end_message_by)
    for i, word in enumerate(result.raw_transcript.split()):
        if len(candidate_text + " " + word) > (MAX_MESSAGE_LENGTH - additional_characters):
            texts.append(candidate_text)
            candidate_text = ""
        else:
            candidate_text += " " + word

    # 2: send the messages
    total_texts = len(texts)
    reply_to = result.message_to_edit
    for i, text in enumerate(texts):
        text_to_send = start_message_by + text + end_message_by.format(i + 1, total_texts)
        if i == 0:
            # we edit the "Transcribing voice message..." message
            result.message_to_edit.edit_text(
                text_to_send,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
        elif i + 1 == total_texts:
            # we are sending the last message
            text_to_send = start_message_by + text + '</i>" <b>[{i}/{tot}] [{conf} {elapsed}"]</b>'.format(
                i=i + 1,
                tot=total_texts,
                conf=result.confidence,
                elapsed=result.elapsed
            )
            reply_to.reply_html(text_to_send, disable_web_page_preview=True, quote=True)
        else:
            # save the last message we sent so we can reply to it the next cicle
            reply_to = reply_to.reply_html(text_to_send, disable_web_page_preview=True, quote=True)

    return total_texts
