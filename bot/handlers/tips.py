import logging

# noinspection PyPackageRequirements
from telegram.ext import CommandHandler, Filters
# noinspection PyPackageRequirements
from telegram import Update

from bot import sttbot
from bot.decorators import decorators
from config import config

logger = logging.getLogger(__name__)

TEXT = """<b>Alcuni suggerimenti sull'utilizzo del bot</b>
- puoi silenziare questa chat per disabilitare le notifiche che ricevi quando il bot ti risponde in un gruppo
- il primo numero in piccolo che compare dopo una trascrizione è un decimale che va da 0.00 a 1.00, \
e rappresenta la "fiducia" nella trascrizione di Google. Il secondo, invece, è il tempo impiegato da \
Google per restituire la trascrizione del vocale
- il bot non trascrive i messaggi vocali inoltrati inviati originariamente da utenti che hanno fatto l'opt-out"""


@decorators.catchexceptions()
def on_tips_command(update: Update, _):
    logger.info("/tips")

    update.message.reply_html(TEXT, disable_web_page_preview=True)


sttbot.add_handler(CommandHandler(["tips", "help"], on_tips_command, filters=Filters.private))
