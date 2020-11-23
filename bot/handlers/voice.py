import logging
from typing import List, Tuple, Union

from sqlalchemy.orm import Session
from google.cloud.speech import (
    SpeechClient,
    RecognitionConfig,
    RecognitionAudio,
    RecognizeResponse,
    SpeechRecognitionResult,
    SpeechRecognitionAlternative
)
# noinspection PyPackageRequirements
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters, MessageHandler
)
# noinspection PyPackageRequirements
from telegram import (
    ChatAction,
    Update, ParseMode, Message
)

from bot import stickersbot
from bot.decorators import decorators
from bot.database.models.user import User
from bot.utilities import utilities
from google.speechtotext import VoiceMessageLocal
from google.speechtotext import VoiceMessageRemote
from config import config

logger = logging.getLogger(__name__)

TEXT_HIDDEN_SENDER = """Mi dispiace, il mittente di questo messaggio vocale ha reso il proprio account non \
accessibile tramite i messaggi inoltrati, quindi non posso verificare che abbia accettato i termini di servizio"""


def recognize_voice(voice: [VoiceMessageLocal, VoiceMessageRemote], update: Update) -> Tuple[Message, Union[str, None]]:
    if voice.short:
        text = "<i>Inizio trascrizione...</i>"
    else:
        text = "<i>Inizio trascrizione... Per i vocali > 1 minuto potrebbe volerci un po' di più</i>"

    message_to_edit = update.message.reply_html(text, disable_notification=True, quote=True)

    raw_transcript, confidence = voice.recognize(punctuation=False)

    if not raw_transcript:
        logger.warning("request for voice message \"%s\" returned empty response (file not deleted)", voice.file_path)
        # do not cleanup the file
        return message_to_edit, None

    # print('\n'.join([f"{round(a.confidence, 2)}: {a.transcript}" for a in result]))

    transcription = f"\"<i>{raw_transcript}</i>\" <b>[{confidence} {voice.hertz_rate_str}]</b>"

    if config.misc.remove_downloaded_files:
        voice.cleanup()

    return message_to_edit, transcription


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session(pass_user=True)
@decorators.ensure_tos(send_accept_message=True)
def on_voice_message_private_chat(update: Update, *args, **kwargs):
    logger.info("voice message in a private chat")

    voice = VoiceMessageLocal.from_message(update.message, download=True)

    message_to_edit, transcription = recognize_voice(voice, update)

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
@decorators.pass_session(pass_user=True)
def on_voice_message_private_chat_forwarded(update: Update, _, session: Session, user: User):
    logger.info("forwarded voice message in a private chat")

    if not utilities.is_admin(update.effective_user):
        if not update.message.forward_from and update.message.forward_sender_name:
            logger.info("forwarded message: original sender hidden their account")
            update.message.reply_html(TEXT_HIDDEN_SENDER)
            return
        else:
            user: [User, None] = session.query(User).filter(User.user_id == update.message.forward_from.id).one_or_none()
            if not user or not user.tos_accepted:
                logger.info("forwarded message: no user in db, or user did not accept tos")
                update.message.reply_html(
                    "<i>Mi dispiace, il mittente di questo messaggio non ha acconsentito al trattamento dei suoi dati</i>",
                    quote=True
                )
                return

    voice = VoiceMessageLocal.from_message(update.message)

    message_to_edit, transcription = recognize_voice(voice, update)

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
@decorators.pass_session(pass_user=True)
def on_voice_message_group_chat(update: Update, _, session: Session, user: User, *args, **kwargs):
    logger.info("voice message in a group chat")

    # ignore:
    # - forwarded voice messages from users who did not accept the ToS
    # - forwarded voice messages from user who hid their accounts
    # - voice messages from members that did not accept the ToS

    if update.message.forward_from or update.message.forward_sender_name:
        # the message is a forwarded message
        if not update.message.forward_from and update.message.forward_sender_name:
            logger.info("forwarded message: original sender hidden their account")
            return

        user: [User, None] = session.query(User).filter(User.user_id == update.message.forward_from.id).one_or_none()
        if not user or not user.tos_accepted:
            logger.info("forwarded message: no user in db, or user did not accept tos")
            return

    if not user.tos_accepted:
        logger.info("user did not accept tos")
        return

    voice = VoiceMessageLocal.from_message(update.message, download=True)

    message_to_edit, transcription = recognize_voice(voice, update)

    if not transcription:
        message_to_edit.delete()
    else:
        message_to_edit.edit_text(
            transcription,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )


stickersbot.add_handler(MessageHandler(
    Filters.private & Filters.voice & ~Filters.forwarded,
    on_voice_message_private_chat,
    run_async=True
))
stickersbot.add_handler(MessageHandler(
    Filters.private & Filters.voice & Filters.forwarded,
    on_voice_message_private_chat_forwarded,
    run_async=True
))
stickersbot.add_handler(MessageHandler(Filters.group & Filters.voice, on_voice_message_group_chat, run_async=True))
