import datetime
import logging
from typing import Tuple, Union

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import Filters, MessageHandler
# noinspection PyPackageRequirements
from telegram import ChatAction, Update, ParseMode, Message

from bot import sttbot
from bot.custom_filters import CFilters
from bot.decorators import decorators
from bot.database.models.chat import Chat
from bot.database.models.user import User
from bot.database.models.transcription_request import TranscriptionRequest
from bot.database.queries import transcription_request
from bot.utilities import utilities
from google.speechtotext import VoiceMessageLocal
from google.speechtotext import VoiceMessageRemote
from google.speechtotext.exceptions import UnsupportedFormat
from config import config

logger = logging.getLogger(__name__)

TEXT_HIDDEN_SENDER = """Mi dispiace, il mittente di questo messaggio vocale ha reso il proprio account non \
accessibile tramite i messaggi inoltrati, quindi non posso verificare che abbia accettato i termini di servizio"""


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

    transcription = f"\"<i>{raw_transcript}</i>\" <b>[{confidence} {voice.sample_rate_str} {elapsed}\"]</b>"

    if config.misc.remove_downloaded_files:
        voice.cleanup()

    return message_to_edit, transcription


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session(pass_user=True)
@decorators.ensure_tos(send_accept_message=True)
def on_voice_message_private_chat(update: Update, _, session: Session, *args, **kwargs):
    logger.info("voice message in a private chat, mime type: %s", update.message.voice.mime_type)

    voice = VoiceMessageLocal.from_message(update.message)

    message_to_edit, transcription = recognize_voice(voice, update, session)

    if not transcription:
        message_to_edit.edit_text("<i>Impossibile trascrivere messaggio vocale</i>", parse_mode=ParseMode.HTML)
    else:
        message_to_edit.edit_text(
            transcription,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )


@decorators.failwithmessage
@decorators.ensure_tos(send_accept_message=True)
def on_large_voice_message_private_chat(update: Update, *args, **kwargs):
    logger.info("voice message is too large (%d bytes)", update.message.voice.file_size)

    update.message.reply_html("Questo vocale è troppo pesante", quote=True)


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session(pass_user=True, commit_on_exception=True)
def on_voice_message_private_chat_forwarded(update: Update, _, session: Session, user: User):
    logger.info("forwarded voice message in a private chat, mime type: %s", update.message.voice.mime_type)

    if not utilities.is_admin(update.effective_user) and not user.superuser:
        if utilities.user_hidden_account(update.message):
            logger.info("forwarded message: original sender hidden their account")
            update.message.reply_html(TEXT_HIDDEN_SENDER)
            return
        else:
            user: [User, None] = session.query(User).filter(User.user_id == update.message.forward_from.id).one_or_none()
            if not user or not user.tos_accepted:
                logger.info("forwarded message: no user in db, or user did not accept tos")
                update.message.reply_html(
                    "Mi dispiace, il mittente di questo messaggio non ha acconsentito al trattamento dei suoi dati",
                    quote=True
                )
                return
    elif user.superuser:
        logger.info("user forwards are whitelisted (superuser)")

    voice = VoiceMessageLocal.from_message(update.message)

    message_to_edit, transcription = recognize_voice(voice, update, session)

    if not transcription:
        message_to_edit.edit_text("<i>Impossibile trascrivere messaggio vocale</i>", parse_mode=ParseMode.HTML)
    else:
        message_to_edit.edit_text(
            transcription,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session(pass_user=True, pass_chat=True)
def on_voice_message_group_chat(update: Update, _, session: Session, user: User, chat: Chat, *args, **kwargs):
    logger.info("voice message in a group chat")

    # ignore:
    # - forwarded voice messages from users who did not accept the ToS
    # - forwarded voice messages from user who hid their accounts
    # - voice messages from members that did not accept the ToS

    if not chat.ignore_tos:
        if utilities.user_hidden_account(update.message):
            # the message is a forwarded message
            logger.info("forwarded message: original sender hidden their account")
            return

        user: [User, None] = session.query(User).filter(User.user_id == update.message.forward_from.id).one_or_none()
        if not user or not user.tos_accepted:
            logger.info("forwarded message: no user in db, or user did not accept tos")
            return

        if not user.tos_accepted:
            logger.info("user did not accept tos")
            return
    else:
        # if chat.ignore_tos is true, don't make any control on whether the sender of audios sent in this chat
        # have accepted the data usage notice or not
        logger.info("chat %d is set to ignore data agreement of users", update.effective_chat.id)

    if update.message.voice.file_size and update.message.voice.file_size > config.telegram.voice_max_size:
        logger.info("voice message is too large (%d bytes)", update.message.voice.file_size)
        return

    voice = VoiceMessageLocal.from_message(update.message, download=True)

    message_to_edit, transcription = recognize_voice(voice, update, session, punctuation=chat.punctuation)

    if not transcription:
        message_to_edit.delete()
    else:
        message_to_edit.edit_text(
            transcription,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )


sttbot.add_handler(MessageHandler(
    Filters.private & Filters.voice & CFilters.voice_too_large,
    on_large_voice_message_private_chat
))
sttbot.add_handler(MessageHandler(
    Filters.private & Filters.voice & ~Filters.forwarded,
    on_voice_message_private_chat,
    run_async=True
))
sttbot.add_handler(MessageHandler(
    Filters.private & Filters.voice & Filters.forwarded,
    on_voice_message_private_chat_forwarded,
    run_async=True
))
sttbot.add_handler(MessageHandler(Filters.group & Filters.voice, on_voice_message_group_chat, run_async=True))
