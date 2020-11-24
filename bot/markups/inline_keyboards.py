# noinspection PyPackageRequirements
from telegram import InlineKeyboardMarkup, InlineKeyboardButton


class InlineKeyboard:
    HIDE = None
    REMOVE = None

    TOS_SHOW = InlineKeyboardMarkup([[InlineKeyboardButton('leggi disclaimer', callback_data='tos:show')]])
    TOS_AGREE = InlineKeyboardMarkup([[InlineKeyboardButton('accetta', callback_data='tos:agree')]])
    TOS_REVOKE = InlineKeyboardMarkup([[InlineKeyboardButton('revoca il consenso', callback_data='tos:revoke')]])
