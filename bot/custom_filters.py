# noinspection PyPackageRequirements
from telegram.ext import MessageFilter

from bot.utilities import utilities
from config import config


class FromAdmin(MessageFilter):
    def filter(self, message):
        return utilities.is_admin(message.from_user)


class VoiceTooLarge(MessageFilter):
    def filter(self, message):
        return message.voice.file_size and message.voice.file_size > config.telegram.voice_max_size


class CFilters:
    from_admin = FromAdmin()
    voice_too_large = VoiceTooLarge()
