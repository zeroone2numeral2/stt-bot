import logging

# noinspection PyUnresolvedReferences,PyPackageRequirements
import os

# noinspection PyUnresolvedReferences,PyPackageRequirements
from telegram.utils.request import Request

from .utilities import utilities
from .database import base
from .bot import VoiceMessagesBot
from config import config

logger = logging.getLogger(__name__)

sttbot = VoiceMessagesBot(
    token=config.telegram.token,
    use_context=True,
    workers=config.telegram.get("workers", 4),
    persistence=utilities.persistence_object(config.telegram.persistence) if config.telegram.persistence else None,
)


def main():
    utilities.load_logging_config('logging.json')

    sttbot.import_handlers(r'bot/handlers/')
    sttbot.run(clean=True)


if __name__ == '__main__':
    main()
