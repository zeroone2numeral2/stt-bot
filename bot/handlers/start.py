import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters
)
# noinspection PyPackageRequirements
from telegram import (
    ChatAction,
    Update
)

from bot import sttbot
from bot.database.models.user import User
from bot.decorators import decorators
from config import config

logger = logging.getLogger(__name__)

TEXT = """Ciao! Sono un bot che permette di trascrivere i messaggi vocali inviati dagli utenti di in gruppo, \
utilizzando la <a href="https://cloud.google.com/speech-to-text/">trascrizione vocale di Google</a>

Usa /tips o /help per ricevere alcuni suggerimenti sull'utilizzo del bot"""


@decorators.catchexceptions()
@decorators.pass_session(pass_user=True)
@decorators.ensure_tos(send_accept_message=True, send_accept_message_after_callback=True)
def on_start_command(update: Update, _, session: [Session, None], user: [User, None]):
    logger.info("/start")

    update.message.reply_html(TEXT, disable_web_page_preview=True)


sttbot.add_handler(CommandHandler("start", on_start_command, filters=Filters.private))
