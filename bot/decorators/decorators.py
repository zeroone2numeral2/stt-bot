import logging
from functools import wraps

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.error import TimedOut
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from bot.database.base import get_session
from bot.database.models.user import User
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


def ensure_tos(send_accept_message=False, send_accept_message_after_callback=False):
    """Make sure the user accepted the ToS. In group chats, if the ToS is not accepted, the funtion just returns.
    In private chats, it may send a message.

    If 'silently' is true, the bot will just add an info to the context object and continue with the callback
    if 'dont_override_callback' is true, the bot will execute the callback and then send the ToS message. If false,
    the bot will only send the ToS message

    'silently' and 'dont_override_callback' are mutually exclusive"""
    if send_accept_message_after_callback and not send_accept_message:
        raise ValueError("if 'send_accept_message_after_callback' is true, 'send_accept_message' must be true too")

    def real_decorator(func):
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, session: [Session, None] = None, user: [User, None] = None, *args, **kwargs):
            if session is None or user is None:
                raise ValueError("ensure_tos decorator has been called without passing it a Session or User instance")

            if user.tos_accepted or not send_accept_message:
                return func(update, context, session, user, *args, **kwargs)
            elif send_accept_message and update.effective_chat.id > 0:
                callback_result = None
                if send_accept_message_after_callback:
                    callback_result = func(update, context, session, user, *args, **kwargs)

                update.message.reply_html('pls accept tos')

                return callback_result
            else:
                # tos not accepted -> do nothing in groups
                return

        return wrapped

    return real_decorator


def failwithmessage(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            return func(update, context, *args, **kwargs)
        except TimedOut:
            # what should this return when we are inside a conversation?
            logger.error('Telegram exception: TimedOut')
        except Exception as e:
            logger.error('error while running handler callback: %s', str(e), exc_info=True)

            if (update.effective_chat.id > 0 and not config.telegram.silence_exceptions_private) or (update.effective_chat.id < 0 and not config.telegram.silence_exceptions_group):
                text = 'An error occurred while processing the message: <code>{}</code>'.format(utilities.escape_html(str(e)))
                if update.callback_query:
                    update.callback_query.message.reply_html(text, disable_web_page_preview=True)
                else:
                    update.message.reply_html(text, disable_web_page_preview=True)

            # return ConversationHandler.END
            return

    return wrapped


def pass_session(pass_user=True, create_user_if_not_existing=True):
    if create_user_if_not_existing and not pass_user:
        raise ValueError("if 'create_user_if_not_existing' is true, 'pass_user' must be true too")

    def real_decorator(func):
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            # we fetch the session once per message at max, cause the decorator is run only if a message passes filters
            session: Session = get_session()

            user: [User, None] = None
            if pass_user:
                user = session.query(User).filter(User.user_id == update.effective_user.id).one_or_none()

                if not user and create_user_if_not_existing:
                    user = User(user_id=update.effective_user.id)
                    session.add(user)

            result = func(update, context, session=session, user=user, *args, **kwargs)

            session.commit()

            return result

        return wrapped

    return real_decorator
