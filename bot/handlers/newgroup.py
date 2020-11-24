import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import (
    MessageHandler,
    Filters
)
# noinspection PyPackageRequirements
from telegram import (
    ChatAction,
    Update
)

from bot import sttbot
from bot.decorators import decorators
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
def on_new_group_chat(update: Update, _):
    logger.info("new group chat: %s", update.effective_chat.title)

    if utilities.is_admin(update.effective_user) or not config.telegram.exit_unknown_groups:
        return

    logger.info("unauthorized: leaving...")
    update.effective_chat.leave()


sttbot.add_handler(MessageHandler(Filters.status_update.new_chat_members, on_new_group_chat))
