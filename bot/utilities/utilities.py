import os
import json
import logging
import logging.config
import pickle
import time
from pickle import UnpicklingError
from html import escape

# noinspection PyPackageRequirements
from typing import List

from telegram import User, Message, InlineKeyboardMarkup, ChatMember, TelegramError
from telegram.error import BadRequest
from telegram.ext import PicklePersistence

from config import config

logger = logging.getLogger(__name__)


def load_logging_config(file_name='logging.json'):
    with open(file_name, 'r') as f:
        logging_config = json.load(f)

    logging.config.dictConfig(logging_config)


def persistence_object(file_path='persistence/data.pickle'):

    logger.info('unpickling persistence: %s', file_path)
    try:
        # try to load the file
        try:
            with open(file_path, "rb") as f:
                pickle.load(f)
        except FileNotFoundError:
            pass

    except (UnpicklingError, EOFError):
        logger.warning('deserialization failed: removing persistence file and trying again')
        os.remove(file_path)

    return PicklePersistence(
        filename=file_path,
        store_chat_data=False,
        store_bot_data=False
    )


def escape_html(*args, **kwargs):
    return escape(*args, **kwargs)


def is_admin(user: User) -> bool:
    return user.id in config.telegram.admins


def user_hidden_account(message: Message):
    return message.forward_sender_name and not message.forward_from


def is_forward_from_user(message: Message, exclude_service=True, exclude_bots=False):
    """Returns True if the original sender of the message was an user accunt. Will exlcude service account"""

    if message.forward_from and exclude_service and is_service_account(message.forward_from):
        return False
    elif message.forward_from and exclude_bots and message.forward_from.is_bot:
        # message.forward_from always exist with bots because they cannot hide their forwards
        return False

    # return True even when the user decided to hide their account
    return message.forward_sender_name or message.forward_from


def is_reply_to_bot(message: Message):
    if not message.reply_to_message:
        raise ValueError("Message is not a reply to another message")

    return message.reply_to_message.from_user.is_bot


def is_service_account(user: User):
    return user.id in (777000,)


def is_organic_user(user: User):
    return not (is_service_account(user) or user.is_bot)


def kv_dict_to_string(dictionary: dict, sep: str = "\n", return_if_empty=None):
    if not dictionary:
        return return_if_empty

    return sep.join([f"{k}: {v}" for k, v in dictionary.items()])


def human_readable_size(size, precision=2):
    suffixes = ['b', 'kb', 'mb', 'gb', 'tb']
    suffix_index = 0
    while size > 1024 and suffix_index < 4:
        suffix_index += 1  # increment the index of the suffix
        size = size / 1024.0  # apply the division

    return '%.*f %s' % (precision, size, suffixes[suffix_index])


def combine_inline_keyboards(*inline_keyboards):
    inline_keyboards: List[InlineKeyboardMarkup]

    combined_keyboard = []
    for keyboard in inline_keyboards:
        for buttons_row in keyboard.inline_keyboard:
            combined_keyboard.append(buttons_row)

    return InlineKeyboardMarkup(combined_keyboard)


def detect_media(message: Message):
    if message.photo:
        return message.photo
    elif message.video:
        return message.video
    elif message.document:
        return message.document
    elif message.voice:
        return message.voice
    elif message.video_note:
        return message.video_note
    elif message.audio:
        return message.audio
    elif message.sticker:
        return message.sticker


def download_file(message: Message, file_path, retries=5):
    retries = retries or 1

    media_object = detect_media(message)

    logger.debug("downloading voice message to %s", file_path)
    while retries > 0:
        try:
            telegram_file = media_object.get_file()
            telegram_file.download(file_path)
            retries = 0
        except (BadRequest, TelegramError) as e:
            if "temporarily unavailable" in e.message.lower():
                logger.warning("downloading voice %s raised error: %s", media_object.file_id, e.message)
                time.sleep(2)
                retries -= 1
            else:
                raise
