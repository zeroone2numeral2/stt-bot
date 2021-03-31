import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import CommandHandler, Filters, CallbackContext
# noinspection PyPackageRequirements
from telegram import Update, ChatMember

from bot import sttbot
from bot.bot import AdminPermission
from bot.database.models.chat import Chat
from bot.database.queries import chat as chat_queries
from bot.decorators import decorators
from config import config

logger = logging.getLogger(__name__)


@decorators.catchexceptions()
@decorators.pass_session(pass_chat=True)
@decorators.administrator(skip_refresh=True)
def on_refresh_administrators_command(update: Update, _, session: Session, chat: Chat):
    logger.info("/refreshadmins")

    administrators: [ChatMember] = update.effective_chat.get_administrators()
    chat_queries.update_administrators(session, chat, administrators)

    update.message.reply_html(f"Fatto, {len(chat.chat_administrators)} amministratori salvati")


@decorators.catchexceptions()
@decorators.pass_session(pass_chat=True)
@decorators.administrator()
@decorators.ensure_args(min_number=1)
def on_punctuation_command(update: Update, context: CallbackContext, session: Session, chat: Chat):
    logger.info("/punctuation")

    new_status = context.args[0].lower()
    if new_status == "on":
        new_status = True
    elif new_status == "off":
        new_status = False
    else:
        update.message.reply_html("Utilizzo: <code>/punctuation on</code> oppure <code>/punctuation off</code>")
        return

    chat.punctuation = new_status
    session.add(chat)

    answer = "Punteggiatura abilitata" if new_status else "Punteggiatura disabilitata"
    update.message.reply_html(answer)


sttbot.add_handler(CommandHandler(["punctuation", "punct"], on_punctuation_command, filters=Filters.chat_type.groups))
sttbot.add_handler(CommandHandler(["refreshadmins"], on_refresh_administrators_command, filters=Filters.chat_type.groups))
