# noinspection PyPackageRequirements
from google.cloud.speech import SpeechClient
from google.cloud.storage import Client as StorageClient

from config import config


speech_client = SpeechClient.from_service_account_json(config.google.service_account_json)
storage_client = StorageClient.from_service_account_json(config.google.service_account_json)
