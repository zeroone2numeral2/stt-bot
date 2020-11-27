import datetime
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
from bot.database.models.transcription_request import TranscriptionRequest
from bot.database.queries import transcription_request
from bot.database.queries import user as quser
from bot.decorators import decorators
from bot.utilities import helpers
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)


@decorators.catchexceptions()
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
        update.message.reply_text("Gli amministratori del bot sono già superuser")
        return

    return update.message.reply_to_message.from_user


def get_or_create_user(session: Session, user_id: int) -> User:
    user = session.query(User).filter(User.user_id == user_id).one_or_none()

    if not user:
        user = User(user_id=user_id)
        session.add(user)

    return user


def toggle_superuser(session: Session, tg_user: TelegramUser):
    user_first_name = utilities.escape_html(tg_user.first_name)
    user: User = get_or_create_user(session, tg_user.id)

    if not user.superuser:
        user.make_superuser(name=tg_user.full_name)
        return f"{user_first_name} è superuser, potrà aggiungermi a gruppi/inoltrarmi vocali da trascrivere"
    else:
        user.revoke_superuser()
        return f"{user_first_name} non è più superuser"


@decorators.catchexceptions()
@decorators.pass_session()
def on_superuser_command_group(update: Update, _, session: Session):
    logger.info("/superuser command in a group")

    target_user = detect_user_utility_group(update)
    if not target_user:
        return

    answer = toggle_superuser(session, target_user)

    update.message.reply_html(answer)


@decorators.catchexceptions()
@decorators.pass_session()
def on_superuser_command_private(update: Update, _, session: Session):
    logger.info("/super command in private")

    target_user = detect_user_utility_private(update)
    if not target_user:
        return

    answer = toggle_superuser(session, target_user)

    update.message.reply_html(answer, quote=True)


@decorators.catchexceptions()
@decorators.pass_session()
def on_list_superusers_command(update: Update, _, session: Session):
    logger.info("/superusers command")

    superusers = quser.superusers(session)
    if not superusers:
        update.message.reply_html("Non ci sono superuser salvati")
        return

    names = [user.name for user in superusers]
    update.message.reply_text(f"Superusers: {', '.join(names)}")


@decorators.catchexceptions()
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


@decorators.catchexceptions()
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


@decorators.catchexceptions(force_message_on_exception=True)
@decorators.pass_session()
def on_r_command(update: Update, context: CallbackContext, session: Session):
    logger.info("/r command, args: %s", context.args)

    if not update.message.reply_to_message.voice:
        update.message.reply_html("Rispondi ad un messaggio vocale", quote=True)
        return

    if not context.args:
        voice = VoiceMessageLocal.from_message(update.message.reply_to_message)
    else:
        sample_rate = int(context.args[0])
        voice = VoiceMessageLocal.from_message(update.message.reply_to_message, force_sample_rate=sample_rate)

    avg_response_time = transcription_request.estimated_duration(session, voice.duration)

    voice.parse_sample_rate()  # we parse it so we can include it in the message we send

    message_to_edit = update.message.reply_to_message.reply_html(f"Inizio la trascrizione\n"
                                                                 f"<code>sample rate: {voice.sample_rate_str}\n"
                                                                 f"forced sample rate: {voice.forced_sample_rate_str}\n"
                                                                 f"expected time: {avg_response_time}</code>", quote=True)

    request = TranscriptionRequest(audio_duration=voice.duration)
    start = datetime.datetime.now()

    raw_transcript, confidence = voice.recognize(punctuation=config.google.punctuation)

    end = datetime.datetime.now()
    elapsed = round((end - start).total_seconds(), 1)

    if raw_transcript:
        request.successful(elapsed, sample_rate=voice.sample_rate)
        session.add(request)  # add the request instance to the session only on success

    transcription = f"{raw_transcript}\n" \
                    f"<code>confidence: {confidence}\n" \
                    f"detected sample rate: {voice.sample_rate_str}\n" \
                    f"forced sample rate: {voice.forced_sample_rate_str}\n" \
                    f"estimated time: {avg_response_time}\n" \
                    f"elapsed time: {elapsed}</code>"

    message_to_edit.edit_text(
        transcription,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )


@decorators.catchexceptions(force_message_on_exception=True)
@decorators.pass_session()
def on_parse_command(update: Update, context: CallbackContext, session: Session):
    logger.info("/parse command, args: %s", context.args)

    if not update.message.reply_to_message.voice:
        update.message.reply_html("Rispondi ad un messaggio vocale", quote=True)
        return

    voice = VoiceMessageLocal.from_message(update.message.reply_to_message)

    voice.parse_sample_rate()
    voice.cleanup()

    avg_response_time = transcription_request.estimated_duration(session, voice.duration) or '-'

    update.message.reply_to_message.reply_html(
        f"<code>"
        f"[DB]\n"
        f"estimated time: {avg_response_time}\n"
        f"\n"
        f"[HEADER DATA]\n"
        f"{utilities.kv_dict_to_string(voice.parsed_header_data, return_if_empty='-')}\n"
        f"\n"
        f"[TG]\n"
        f"size: {utilities.human_readable_size(update.message.reply_to_message.voice.file_size)}\n"
        f"mime type: {update.message.reply_to_message.voice.mime_type}"
        f"</code>",
        quote=True
    )


@decorators.catchexceptions(force_message_on_exception=True)
@decorators.pass_session(pass_chat=True)
def on_testignore_command(update: Update, context: CallbackContext, session: Session, chat: Chat, *args, **kwargs):
    logger.info("/testignore command, args: %s", context.args)

    user_id_override = update.message.reply_to_message.from_user.id
    user = session.query(User).filter(User.user_id == user_id_override).one_or_none()
    if not user:
        user = User(user_id=user_id_override)
        session.add(user)

    ignore, reason = helpers.ignore_message_group(session, user, chat, update.message.reply_to_message)
    update.message.reply_html(
        f"<b>{'Ignore' if ignore else 'Ok'}</b> > {reason}",
        quote=True
    )


sttbot.add_handler(CommandHandler("ignoretos", on_ignoretos_command, filters=Filters.group & CFilters.from_admin))
sttbot.add_handler(CommandHandler(["superuser", "su"], on_superuser_command_group, filters=Filters.group & CFilters.from_admin))
sttbot.add_handler(CommandHandler(["superuser", "su"], on_superuser_command_private, filters=Filters.private & CFilters.from_admin))
sttbot.add_handler(CommandHandler(["superusers", "sus"], on_list_superusers_command, filters=Filters.private & CFilters.from_admin))
sttbot.add_handler(MessageHandler(Filters.private & Filters.forwarded & CFilters.from_admin, on_forwarded_message))
sttbot.add_handler(CommandHandler("cleandl", on_cleandl_command, filters=Filters.private & CFilters.from_admin))
sttbot.add_handler(CommandHandler("r", on_r_command, filters=Filters.reply & CFilters.from_admin))
sttbot.add_handler(CommandHandler(["parse", "p"], on_parse_command, filters=Filters.reply & CFilters.from_admin))
sttbot.add_handler(CommandHandler(["testignore"], on_testignore_command, filters=Filters.group & Filters.reply & CFilters.from_admin))
