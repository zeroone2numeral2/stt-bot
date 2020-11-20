import logging
from typing import List

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
    Update, ParseMode
)

from bot import stickersbot
from bot.decorators import decorators
from google.speechtotext import VoiceMessageLocal
from google.speechtotext import VoiceMessageRemote
from config import config

logger = logging.getLogger(__name__)

TEXT = """Ciao! Sono un bot che permette di trascrivere i messaggi vocali inviati dagli utenti di in gruppo, \
utilizzando la <a href="https://cloud.google.com/speech-to-text/">trascrizione vocale di Google</a>

Usa /help per visualizzare tutti i comandi"""


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session(pass_user=True)
@decorators.ensure_tos(send_accept_message=True)
def on_voice_message_private_chat(update: Update, *args, **kwargs):
    logger.info('voice message in a private chat')

    if config.google.bucket_name:
        voice = VoiceMessageRemote.from_message(update.message, bucket_name=config.google.bucket_name)
    else:
        voice = VoiceMessageLocal.from_message(update.message)

    if voice.short:
        text = "<i>Inizio trascrizione...</i>"
    else:
        text = "<i>Inizio trascrizione... Per i vocali > 1 minuto potrebbe volerci un po' di più</i>"

    message_to_edit = update.message.reply_html(text)

    result: List[SpeechRecognitionAlternative] = voice.recognize()

    alternative = result[0]
    transcription = '<i>{}</i> [{}]'.format(alternative.confidence, alternative.confidence)

    message_to_edit.edit_text(
        transcription,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML,
        disable_notification=True,
        quote=True
    )


stickersbot.add_handler(MessageHandler(Filters.private & Filters.voice & ~Filters.forwarded, on_voice_message_private_chat))
