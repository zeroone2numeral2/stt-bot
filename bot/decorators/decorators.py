import datetime
import logging
from functools import wraps
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy.sql import func as sql_func
# noinspection PyPackageRequirements
from telegram import Update, ParseMode, ChatMember
# noinspection PyPackageRequirements
from telegram.error import TimedOut
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from bot.markups import InlineKeyboard
from bot.database.base import get_session
from bot.database.models.user import User
from bot.database.models.chat import Chat
from bot.database.queries import chat as chat_queries
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)


def action(chat_action):
    def real_decorator(func):
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            context.bot.send_chat_action(update.effective_chat.id, chat_action)
            return func(update, context, *args, **kwargs)

        return wrapped

    return real_decorator


def catchexceptions(force_message_on_exception=False):
    def real_decorator(func):
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            try:
                return func(update, context, *args, **kwargs)
            except TimedOut:
                # what should this return when we are inside a conversation?
                logger.error('Telegram exception: TimedOut')
            except Exception as e:
                logger.error('error while running handler callback: %s', str(e), exc_info=True)

                config_send_exception_message = (
                    (update.effective_chat.id > 0 and not config.telegram.silence_exceptions_private)
                    or (update.effective_chat.id < 0 and not config.telegram.silence_exceptions_group)
                )
                if force_message_on_exception or config_send_exception_message:
                    text = 'An error occurred while processing the message: <code>{}</code>'.format(utilities.escape_html(str(e)))
                    if update.callback_query:
                        update.callback_query.message.reply_html(text, disable_web_page_preview=True)
                    else:
                        update.message.reply_html(text, disable_web_page_preview=True)

                # return ConversationHandler.END
                return

        return wrapped

    return real_decorator


def pass_session(
        pass_user=False,
        pass_chat=False,
        create_if_not_existing=True,
        rollback_on_exception=False,
        commit_on_exception=False
):
    # 'rollback_on_exception' should be false by default because we might want to commit
    # what has been added (session.add()) to the session until the exception has been raised anyway.
    # For the same reason, we might want to commit anyway when an exception happens using 'commit_on_exception'

    if all([rollback_on_exception, commit_on_exception]):
        raise ValueError("'rollback_on_exception' and 'commit_on_exception' are mutually exclusive")

    def real_decorator(func):
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            # we fetch the session once per message at max, cause the decorator is run only if a message passes filters
            session: Session = get_session()

            # user: [User, None] = None
            # chat: [Chat, None] = None

            if pass_user:
                user = session.query(User).filter(User.user_id == update.effective_user.id).one_or_none()

                if not user and create_if_not_existing:
                    user = User(user_id=update.effective_user.id)
                    session.add(user)

                kwargs['user'] = user

            if pass_chat:
                if update.effective_chat.id > 0:
                    raise ValueError("'pass_chat' cannot be True for handlers that work in private chats")

                chat = session.query(Chat).filter(Chat.chat_id == update.effective_chat.id).one_or_none()

                if not chat and create_if_not_existing:
                    chat = Chat(chat_id=update.effective_chat.id)
                    session.add(chat)

                kwargs['chat'] = chat

            # noinspection PyBroadException
            try:
                result = func(update, context, session=session, *args, **kwargs)
            except Exception:
                if rollback_on_exception:
                    logger.warning("exception while running an handler callback: rolling back")
                    session.rollback()

                if commit_on_exception:
                    logger.warning("exception while running an handler callback: committing")
                    session.commit()

                # raise the exception anyway, so outher decorators can catch it
                raise

            session.commit()

            return result

        return wrapped

    return real_decorator


def administrator(
        permissions: [None, List] = None,
        _any: bool = True,
        _all: bool = False,
        skip_refresh: bool = False  # to avoid duplicate requests if we want to update the list from the handler
):
    def real_decorator(func):
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            if update.effective_chat.id > 0:
                raise ValueError("decorator does not support private chats")

            if "chat" not in kwargs or "session" not in kwargs:
                raise ValueError("decorator must be wrapped in 'pass_session', and must receive a Chat object")

            user_id = update.effective_user.id

            chat: Chat = kwargs["chat"]
            session: Session = kwargs["session"]

            if chat.last_administrators_fetch:
                admins_fetch_elapsed_seconds = (datetime.datetime.utcnow() - chat.last_administrators_fetch).total_seconds()
            else:
                # if not set, force the refresh
                admins_fetch_elapsed_seconds = (config.telegram.chat_admins_refresh * 3600) + 1

            cache_expired = admins_fetch_elapsed_seconds > config.telegram.chat_admins_refresh * 3600
            if (not skip_refresh and cache_expired) or not chat.chat_administrators:
                logger.info("updating administrators, elapsed seconds: %d", admins_fetch_elapsed_seconds)

                administrators: [ChatMember] = update.effective_chat.get_administrators()
                chat_queries.update_administrators(session, chat, administrators)

            if not chat.is_admin(user_id, permissions, any_permission=_any, all_permissions=_all):
                logger.info("access to decorator-wrapped function forbidden for anauthorized user")
                return
            else:
                return func(update, context, *args, **kwargs)

        return wrapped

    return real_decorator
