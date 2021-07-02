import logging
import os
import importlib
import re
from pathlib import Path

# noinspection PyPackageRequirements
from telegram.error import BadRequest
from telegram.ext import Updater, ConversationHandler
# noinspection PyPackageRequirements
from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeChat

from config import config

logger = logging.getLogger(__name__)


class AdminPermission:
    CAN_MANAGE_CHAT = "can_manage_chat"
    CAN_MANAGE_VOICE_CHAT = "can_manage_voice_chats"
    CAN_CHANGE_INFO = "can_change_info"
    CAN_DELETE_MESSAGES = "can_delete_messages"
    CAN_INVITE_USERS = "can_invite_users"
    CAN_RESTRICT_MEMBERS = "can_restrict_members"
    CAN_PIN_MESSAGES = "can_pin_messages"
    CAN_PROMOTE_MEMBERS = "can_promote_members"


class DummyJob:
    def __init__(self, name):
        self.name = name


class DummyContext:
    def __init__(self, updater, job_name):
        self.updater = updater
        self.job = DummyJob(job_name)


class VoiceMessagesBot(Updater):
    COMMANDS_LIST_REMOVE = []
    USERS_COMMANDS = [
        BotCommand("start", "messaggio di benvenuto"),
        BotCommand("tips", "alcuni suggerimenti sull'utilizzo del bot"),
        BotCommand("optin", "permetti al bot di trascrivere i tuoi vocali"),
        BotCommand("optout", "il bot non trascriverà più i tuoi vocali"),
    ]
    ADMINS_COMMANDS = [
        BotCommand("superuser", "promuovi/depromuovi utente a superuser"),
        BotCommand("superusers", "elenca superusers"),
        BotCommand("cleandl", "elimina file scaricati"),
        BotCommand("parse", "esegui il parsing di un vocale"),
        BotCommand("ti", "testa se un vocale dovrebbe essere ignorato in un gruppo"),
        BotCommand("mi", "output di mediainfo per un vocale"),
        BotCommand("config", "mostra config.toml[behavior]"),
    ]

    @staticmethod
    def _load_manifest(manifest_path):
        if not manifest_path:
            return

        try:
            with open(manifest_path, 'r') as f:
                manifest_str = f.read()
        except FileNotFoundError:
            logger.debug('manifest <%s> not found', os.path.normpath(manifest_path))
            return

        if not manifest_str.strip():
            return

        manifest_str = manifest_str.replace('\r\n', '\n')
        manifest_lines = manifest_str.split('\n')

        modules_list = list()
        for line in manifest_lines:
            line = re.sub(r'(?:\s+)?#.*(?:\n|$)', '', line)  # remove comments from the line
            if line.strip():  # ignore empty lines
                items = line.split()  # split on spaces. We will consider only the first word
                modules_list.append(items[0])  # tuple: (module_to_import, [callbacks_list])

        return modules_list

    @classmethod
    def import_handlers(cls, directory):
        """A text file named "manifest" can be placed in the dir we are importing the handlers from.
        It can contain the list of the files to import, the bot will import only these
        modules as ordered in the manifest file.
        Inline comments are allowed, they must start by #"""

        paths_to_import = list()

        manifest_modules = cls._load_manifest(os.path.join(directory, 'manifest'))
        if manifest_modules:
            # build the base import path of the plugins/jobs directory
            target_dir_path = os.path.splitext(directory)[0]
            target_dir_import_path_list = list()
            while target_dir_path:
                target_dir_path, tail = os.path.split(target_dir_path)
                target_dir_import_path_list.insert(0, tail)
            base_import_path = '.'.join(target_dir_import_path_list)

            for module in manifest_modules:
                import_path = base_import_path + module

                logger.debug('importing module: %s', import_path)

                paths_to_import.append(import_path)
        else:
            for path in sorted(Path(directory).rglob('*.py')):
                file_path = os.path.splitext(str(path))[0]

                import_path = []

                while file_path:
                    file_path, tail = os.path.split(file_path)
                    import_path.insert(0, tail)

                import_path = '.'.join(import_path)

                paths_to_import.append(import_path)

        for import_path in paths_to_import:
            logger.debug('importing module: %s', import_path)
            importlib.import_module(import_path)

    def set_commands(self):
        self.bot.set_my_commands(self.USERS_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        self.bot.set_my_commands([], scope=BotCommandScopeAllGroupChats())

        admin_commands = self.USERS_COMMANDS + self.ADMINS_COMMANDS
        for admin_id in config.telegram.admins:
            try:
                self.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
            except BadRequest as e:
                if "chat not found" in e.message.lower():
                    logger.warning("make sure admin <%d> started me!", admin_id)
                else:
                    raise

    def run(self, *args, **kwargs):
        logger.info('updating commands list...')
        self.set_commands()

        logger.info("allowed updates: %s", ", ".join(kwargs["allowed_updates"] if "allowed_updates" in kwargs else "?"))

        logger.info('running as @%s', self.bot.username)
        self.start_polling(*args, **kwargs)
        self.idle()

    def add_handler(self, *args, **kwargs):
        if isinstance(args[0], ConversationHandler):
            # ConverstaionHandler.name or the name of the first entry_point function
            logger.info('adding conversation handler: %s', args[0].name or args[0].entry_points[0].callback.__name__)
        else:
            logger.info('adding handler: %s', args[0].callback.__name__)

        self.dispatcher.add_handler(*args, **kwargs)
