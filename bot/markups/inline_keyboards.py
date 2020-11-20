# noinspection PyPackageRequirements
from telegram import InlineKeyboardMarkup, InlineKeyboardButton


class InlineKeyboard:
    HIDE = None
    REMOVE = None

    TERMS_AGREE = InlineKeyboardMarkup([[InlineKeyboardButton('accetta', callback_data='termsagree')]])
