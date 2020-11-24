import logging
import os

from sqlalchemy.orm import Session
from sqlalchemy import inspect
# noinspection PyPackageRequirements
from telegram.ext import MessageHandler, Filters, CommandHandler, CallbackContext
# noinspection PyPackageRequirements
from telegram import ChatAction, Update, User as TelegramUser, Message, ParseMode

from bot import sttbot
from bot.custom_filters import CFilters
from google.speechtotext import VoiceMessageLocal
from bot.database.models.chat import Chat
from bot.database.models.user import User
from bot.decorators import decorators
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)


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


def detect_user_utility_private(update: Update) -> [TelegramUser, None]:
    message: Message = update.message
    replied_to_message: Message = message.reply_to_message
    if not replied_to_message or not utilities.is_forward_from_user(replied_to_message, exclude_bots=True):
        update.message.reply_text("Rispondi al messaggio inoltrato il cui mittente originale è un utente")
        return

    if utilities.user_hidden_account(replied_to_message):
        update.message.reply_text("Il mittente ha nascosto il proprio account")
        return

    if replied_to_message.forward_from.id == update.message.from_user.id:
        update.message.reply_text("Gli amministratori del bot possono sempre aggiungerlo a gruppi")
        return

    return replied_to_message.forward_from


def detect_user_utility_group(update: Update) -> [TelegramUser, None]:
    if not update.message.reply_to_message or not utilities.is_organic_user(update.message.reply_to_message.from_user):
        update.message.reply_text("Rispondi ad un utente")
        return

    if update.message.reply_to_message.from_user.id == update.message.from_user.id:
        update.message.reply_text("Gli amministratori del bot possono sempre aggiungerlo a gruppi")
        return

    return update.message.reply_to_message.from_user


def get_or_create_user(session: Session, user_id: int) -> User:
    user = session.query(User).filter(User.user_id == user_id).one_or_none()

    if not user:
        user = User(user_id=user_id)
        session.add(user)

    return user


def toggle_add_group(session: Session, tg_user: TelegramUser):
    user_first_name = utilities.escape_html(tg_user.first_name)
    user: User = get_or_create_user(session, tg_user.id)

    if not user.can_add_to_groups:
        user.can_add_to_groups = True
        return f"{user_first_name} potrà aggiungermi a chat di gruppo"
    else:
        user.can_add_to_groups = False
        return f"{user_first_name} non potrà più aggiungermi a chat di gruppo"


def toggle_whitelisted_forwards(session: Session, tg_user: TelegramUser):
    user_first_name = utilities.escape_html(tg_user.first_name)
    user: User = get_or_create_user(session, tg_user.id)

    if not user.whitelisted_forwards:
        user.whitelisted_forwards = True
        return f"{user_first_name} potrà inoltrarmi qualsiasi vocale da trascrivere"
    else:
        user.whitelisted_forwards = False
        return f"{user_first_name} non potrà più inoltrarmi qualsiasi vocale da trascrivere"


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session()
def on_addgroups_command_group(update: Update, _, session: Session):
    logger.info("/addgroups command in a group")

    target_user = detect_user_utility_group(update)
    if not target_user:
        return

    answer = toggle_add_group(session, target_user)

    update.message.reply_html(answer)


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session()
def on_addgroups_command_private(update: Update, _, session: Session):
    logger.info("/addgroups command in private")

    target_user = detect_user_utility_private(update)
    if not target_user:
        return

    answer = toggle_add_group(session, target_user)

    update.message.reply_html(answer, quote=True)


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session()
def on_wforwards_command_group(update: Update, _, session: Session):
    logger.info("/wforwards command in a group")

    target_user = detect_user_utility_group(update)
    if not target_user:
        return

    answer = toggle_whitelisted_forwards(session, target_user)

    update.message.reply_html(answer)


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session()
def on_wforwards_command_private(update: Update, _, session: Session):
    logger.info("/wforwards command in private")

    target_user = detect_user_utility_private(update)
    if not target_user:
        return

    answer = toggle_whitelisted_forwards(session, target_user)

    update.message.reply_html(answer, quote=True)


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
@decorators.pass_session()
def on_forwarded_message(update: Update, _, session: Session):
    logger.info("forwarded message from admin")

    if not utilities.is_forward_from_user(update.message, exclude_bots=True):
        update.message.reply_text("Inoltrami un messaggio il cui mittente originale è un utente")
        return

    if utilities.user_hidden_account(update.message):
        update.message.reply_text("Il mittente ha nascosto il proprio account")
        return

    tg_user = update.message.forward_from
    user_first_name = utilities.escape_html(tg_user.first_name)
    user = session.query(User).filter(User.user_id == tg_user.id).one_or_none()

    if not user:
        update.message.reply_html(f"{user_first_name} non è nel database")
        return

    columns = []
    model_inspection = inspect(user)
    for column_attr in model_inspection.mapper.column_attrs:
        key = column_attr.key
        value = getattr(user, key)
        columns.append((key, value))

    update.message.reply_text("\n".join([f"{k}: {v}" for k, v in columns]))


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
def on_cleandl_command(update: Update, _):
    logger.info("/cleandl command")

    dir_path = r"downloads/"

    deleted_count = 0
    for file_name in os.listdir(dir_path):
        if file_name.startswith("."):
            continue

        file_path = os.path.join(dir_path, file_name)
        if os.path.isdir(file_name):
            continue

        os.remove(file_path)
        deleted_count += 1

    update.message.reply_html(f"Deleted {deleted_count} files")


@decorators.action(ChatAction.TYPING)
@decorators.failwithmessage
def on_sr_command(update: Update, context: CallbackContext):
    logger.info("/sr command, args: %s", context.args)

    if not context.args:
        update.message.reply_html("Specifica un sample rate (in hertz)", quote=True)
        return

    if not update.message.reply_to_message.voice:
        update.message.reply_html("Rispondi ad un messaggio vocale", quote=True)
        return

    sample_rate = int(context.args[0])

    voice = VoiceMessageLocal.from_message(update.message.reply_to_message, force_sample_rate=sample_rate)

    message_to_edit = update.message.reply_to_message.reply_html(f"Inizio la trascrizione (hertz: {sample_rate})...")

    raw_transcript, confidence = voice.recognize(punctuation=config.google.punctuation)

    if raw_transcript:
        voice.cleanup()

    transcription = f"{raw_transcript} <b>[{confidence} a:{voice.sample_rate_str}/f:{voice.forced_sample_rate}]</b>"

    message_to_edit.edit_text(
        transcription,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )


sttbot.add_handler(CommandHandler("ignoretos", on_ignoretos_command, filters=Filters.group & CFilters.from_admin))
sttbot.add_handler(CommandHandler("addgroups", on_addgroups_command_group, filters=Filters.group & CFilters.from_admin))
sttbot.add_handler(CommandHandler("addgroups", on_addgroups_command_private, filters=Filters.private & CFilters.from_admin))
sttbot.add_handler(CommandHandler("wforwards", on_wforwards_command_group, filters=Filters.group & CFilters.from_admin))
sttbot.add_handler(CommandHandler("wforwards", on_wforwards_command_private, filters=Filters.private & CFilters.from_admin))
sttbot.add_handler(MessageHandler(Filters.private & Filters.forwarded & CFilters.from_admin, on_forwarded_message))
sttbot.add_handler(CommandHandler("cleandl", on_cleandl_command, filters=Filters.private & CFilters.from_admin))
sttbot.add_handler(CommandHandler("sr", on_sr_command, filters=Filters.reply & CFilters.from_admin))
