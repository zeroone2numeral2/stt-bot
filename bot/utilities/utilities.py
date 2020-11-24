import os
import json
import logging
import logging.config
import pickle
from pickle import UnpicklingError
from html import escape

# noinspection PyPackageRequirements
from telegram import User, Message
from telegram.ext import PicklePersistence

from bot import sttbot
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


def is_forward(message: Message):
    return message.forward_sender_name or message.forward_from


def is_reply_to_bot(message: Message):
    if not message.reply_to_message:
        raise ValueError("Message is not a reply to another message")

    return message.reply_to_message.from_user.is_bot
