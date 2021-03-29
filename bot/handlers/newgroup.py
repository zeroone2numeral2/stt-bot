import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import MessageHandler, Filters, MessageFilter
# noinspection PyPackageRequirements
from telegram import ChatAction, Update, User as TelegramUser, ChatMember
# noinspection PyPackageRequirements
from telegram.utils import helpers as ptb_helpers

from bot import sttbot
from bot.database.models.chat import Chat
from bot.database.models.user import User
from bot.database.models.chat_administrator import ChatAdministrator
from bot.database.queries import chat as chat_queries
from bot.decorators import decorators
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)

DEEPLINK_OPTOUT = ptb_helpers.create_deep_linked_url(sttbot.bot.username, "optout")


class NewGroup(MessageFilter):
    def filter(self, message):
        if message.new_chat_members:
            member: TelegramUser
            for member in message.new_chat_members:
                if member.id == sttbot.bot.id:
                    return True


new_group = NewGroup()


@decorators.catchexceptions()
@decorators.pass_session(pass_user=True, pass_chat=True)
def on_new_group_chat(update: Update, _, session: Session, user: User, chat: Chat):
    logger.info("new group chat: %s", update.effective_chat.title)

    if config.telegram.exit_unknown_groups and not (utilities.is_admin(update.effective_user) or user.superuser):
        logger.info("unauthorized: leaving...")
        update.effective_chat.leave()
        chat.left = True
        return

    update.message.reply_html(
        "<i>Promemoria: se non vuoi che trascriva i tuoi vocali, puoi fare l'opt-out</i> <a href=\"{}\">da qui</a>".format(DEEPLINK_OPTOUT),
        quote=False
    )
    chat.left = None

    administrators: [ChatMember] = update.effective_chat.get_administrators()
    chat_queries.save_administrators(session, chat, administrators)


sttbot.add_handler(MessageHandler(new_group, on_new_group_chat))
