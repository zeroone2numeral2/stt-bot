# noinspection PyPackageRequirements
from telegram.ext import MessageFilter

from bot.utilities import utilities
from config import config


class FromAdmin(MessageFilter):
    def filter(self, message):
        return utilities.is_admin(message.from_user)


class VoiceTooLarge(MessageFilter):
    def filter(self, message):
        voice = message.voice or message.audio
        return voice.file_size and voice.file_size > config.behavior.voice_max_size


class Voice(MessageFilter):
    def filter(self, message):
        return message.voice or (message.audio and utilities.is_whatsapp_voice(message.audio))


class CFilters:
    from_admin = FromAdmin()
    voice_too_large = VoiceTooLarge()
    voice = Voice()
