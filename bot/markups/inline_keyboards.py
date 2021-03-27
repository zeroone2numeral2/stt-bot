# noinspection PyPackageRequirements
from telegram import InlineKeyboardMarkup, InlineKeyboardButton


class InlineKeyboard:
    HIDE = None
    REMOVE = None

    DISCLAIMER_SHOW = InlineKeyboardMarkup([[InlineKeyboardButton('leggi disclaimer sui dati trattati', callback_data='disclaimer:show')]])
    DISCLAIMER_HIDE = InlineKeyboardMarkup([[InlineKeyboardButton('riduci', callback_data='disclaimer:hide')]])
    OPTOUT = InlineKeyboardMarkup([[InlineKeyboardButton('richiedi opt-out', callback_data='optout')]])
    OPTIN = InlineKeyboardMarkup([[InlineKeyboardButton('richiedi opt-in', callback_data='optin')]])
