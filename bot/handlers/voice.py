import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import Filters, MessageHandler
# noinspection PyPackageRequirements
from telegram import ChatAction, Update, ParseMode

from bot import sttbot
from bot.custom_filters import CFilters
from bot.decorators import decorators
from bot.database.models.chat import Chat
from bot.database.models.user import User
from bot.utilities import utilities
from bot.utilities import helpers
from google.speechtotext import VoiceMessageLocal
from config import config

logger = logging.getLogger(__name__)

TEXT_HIDDEN_SENDER = """Mi dispiace, il mittente di questo messaggio vocale ha reso il proprio account non \
accessibile tramite i messaggi inoltrati, quindi non posso verificare che abbia accettato i termini di servizio"""


@decorators.action(ChatAction.TYPING)
@decorators.catchexceptions()
@decorators.pass_session(pass_user=True)
@decorators.ensure_tos(send_accept_message=True)
def on_voice_message_private_chat(update: Update, _, session: Session, *args, **kwargs):
    logger.info("voice message in a private chat, mime type: %s", update.message.voice.mime_type)

    voice = VoiceMessageLocal.from_message(update.message)

    message_to_edit, transcription = helpers.recognize_voice(voice, update, session)

    if not transcription:
        message_to_edit.edit_text("<i>Impossibile trascrivere messaggio vocale</i>", parse_mode=ParseMode.HTML)
    else:
        message_to_edit.edit_text(
            transcription,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )


@decorators.catchexceptions()
@decorators.ensure_tos(send_accept_message=True)
def on_large_voice_message_private_chat(update: Update, *args, **kwargs):
    logger.info("voice message is too large (%d bytes)", update.message.voice.file_size)

    update.message.reply_html("Questo vocale è troppo pesante", quote=True)


@decorators.action(ChatAction.TYPING)
@decorators.catchexceptions()
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

    message_to_edit, transcription = helpers.recognize_voice(voice, update, session)

    if not transcription:
        message_to_edit.edit_text("<i>Impossibile trascrivere messaggio vocale</i>", parse_mode=ParseMode.HTML)
    else:
        message_to_edit.edit_text(
            transcription,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )


@decorators.catchexceptions()
@decorators.pass_session(pass_user=True, pass_chat=True)
def on_voice_message_group_chat(update: Update, _, session: Session, user: User, chat: Chat, *args, **kwargs):
    logger.info("voice message in a group chat")

    ignore_message, _ = helpers.ignore_message_group(session, user, chat, update.message)
    if ignore_message:
        return

    update.message.chat.send_chat_action(ChatAction.TYPING)

    if update.message.voice.file_size and update.message.voice.file_size > config.telegram.voice_max_size:
        logger.info("voice message is too large (%d bytes)", update.message.voice.file_size)
        return

    voice = VoiceMessageLocal.from_message(update.message, download=True)

    message_to_edit, transcription = helpers.recognize_voice(voice, update, session, punctuation=chat.punctuation)

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
