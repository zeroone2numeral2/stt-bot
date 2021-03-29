import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import CommandHandler, Filters
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

    update.message.reply_html("Fatto, {} amministratori salvati".format(len(chat.chat_administrators)))


sttbot.add_handler(CommandHandler(["refreshadmins"], on_refresh_administrators_command, filters=Filters.chat_type.groups))
