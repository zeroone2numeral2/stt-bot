import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import MessageHandler, Filters, MessageFilter, CommandHandler
# noinspection PyPackageRequirements
from telegram import ChatAction, Update, User as TelegramUser, Message

from bot import sttbot
from bot.database.models.chat import Chat
from bot.database.models.user import User
from bot.decorators import decorators
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)


class FromAdmin(MessageFilter):
    def filter(self, message):
        return utilities.is_admin(message.from_user)


from_admin = FromAdmin()


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session(pass_chat=True)
def on_ignoretos_command(update: Update, _, session: Session, chat: Chat):
    logger.info("/ignoretos command")

    if not chat.ignore_tos:
        chat.ignore_tos = True
        answer = "I messaggi vocali in questa chat verranno trascritti a prescindere dalla volontà di chi li invia"
    else:
        chat.ignore_tos = False
        answer = "I messaggi vocali in questa chat verranno trascritti solo se chi li invia ha acconsentito alle " \
                 "modalità dei trattamenti dei propri dati"

    update.message.reply_html(answer)


def edit_add_group(session: Session, tg_user: TelegramUser):
    user_first_name = utilities.escape_html(tg_user.first_name)
    user = session.query(User).filter(User.user_id == tg_user.id).one_or_none()

    if not user:
        user = User(user_id=tg_user.id)
        session.add(user)

    if not user.can_add_to_groups:
        user.can_add_to_groups = True
        return f"{user_first_name} potrà aggiungermi a chat di gruppo"
    else:
        user.can_add_to_groups = False
        return f"{user_first_name} non potrà più aggiungermi a chat di gruppo"


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session()
def on_addgroups_command_group(update: Update, _, session: Session):
    logger.info("/addgroups command in a group")

    if not update.message.reply_to_message or not utilities.is_organic_user(update.message.reply_to_message.from_user):
        update.message.reply_text("Rispondi ad un utente")
        return

    answer = edit_add_group(session, update.message.reply_to_message.from_user)

    update.message.reply_html(answer)


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session()
def on_addgroups_command_private(update: Update, _, session: Session):
    logger.info("/addgroups command in private")

    message: Message = update.message
    replied_to_message: Message = message.reply_to_message
    if not replied_to_message or not utilities.is_forward_from_user(replied_to_message, exclude_bots=True):
        update.message.reply_text("Rispondi al messaggio inoltrato il cui mittente originale è un utente")
        return

    if utilities.user_hidden_account(replied_to_message):
        update.message.reply_text("Il mittente ha nascosto il proprio account")
        return

    answer = edit_add_group(session, replied_to_message.forward_from)

    update.message.reply_html(answer, quote=True)


sttbot.add_handler(CommandHandler("ignoretos", on_ignoretos_command, filters=Filters.group & from_admin))
sttbot.add_handler(CommandHandler("addgroups", on_addgroups_command_group, filters=Filters.group & from_admin))
sttbot.add_handler(CommandHandler("addgroups", on_addgroups_command_private, filters=Filters.private & from_admin))
