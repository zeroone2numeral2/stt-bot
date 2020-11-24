import logging

# noinspection PyPackageRequirements
from telegram.ext import Filters, MessageHandler
# noinspection PyPackageRequirements
from telegram import ChatAction, Update

from bot import sttbot
from bot.custom_filters import CFilters
from bot.decorators import decorators

logger = logging.getLogger(__name__)

TEXT = """Hmm, non capisco cosa tu voglia dire. Inviami/inoltrami un messaggio vocale per trascriverlo, oppure usa \
/tos per dare o revocare il tuo consenso al trattamento dei tuoi dati"""


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
def on_unknown_message(update: Update, _):
    logger.info("unkwnon message in private chat")

    update.message.reply_html(TEXT, disable_web_page_preview=True)


sttbot.add_handler(MessageHandler(Filters.private & ~CFilters.from_admin, on_unknown_message))
