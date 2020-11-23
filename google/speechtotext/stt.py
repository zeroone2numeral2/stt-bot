import io
import os
import logging
from typing import List

# noinspection PyPackageRequirements
from google.cloud.storage import Client as StorageClient
# noinspection PyPackageRequirements
from google.cloud.speech import (
    SpeechClient,
    RecognitionConfig,
    RecognitionAudio,
    RecognizeResponse,
    SpeechRecognitionResult,
    SpeechRecognitionAlternative
)
# noinspection PyPackageRequirements
from telegram import Message

from google.clients import speech_client
from google.clients import storage_client

logger = logging.getLogger(__name__)


class VoiceMessage:
    LANGUAGE = "it-IT"
    # opus hertz rate should always be 48000, but for some reasons google's api sometimes work only when 16000 hertz is
    # specified. This probably depends on the device the voice message has been recorded from, although ffmpeg
    # always says the hertz rate is 48000
    OPUS_HERTZ_RATE = [16000, 48000]

    def __init__(self, file_name, duration: int, download_dir='downloads', max_alternatives: [int, None] = None):
        if duration is None:
            raise ValueError("the voice message duration must be provided")
        elif max_alternatives is not None:
            raise NotImplementedError

        self.file_name = file_name
        self.file_path = os.path.join(download_dir, self.file_name)
        self.duration = duration
        self.short = True
        self.hertz_rate = self.OPUS_HERTZ_RATE[0]
        self.client: SpeechClient = speech_client
        self.max_alternatives = max_alternatives
        self.recognition_audio: [RecognitionAudio, None] = None
        self.recognition_config: [RecognitionConfig, None] = None

        if self.duration > 59:
            self.short = False

    @classmethod
    def from_message(cls, message: Message, download=False, *args, **kwargs):
        if not message.voice:
            raise AttributeError("Message object must contain a voice message")

        if message.voice.duration is None:
            raise ValueError("message.Voice must contain its duration")

        file_name = "{}_{}.ogg".format(message.chat.id, message.message_id)

        voice = cls(
            file_name=file_name,
            duration=message.voice.duration,
            *args,
            **kwargs
        )

        telegram_file = message.voice.get_file()
        telegram_file.download(voice.file_path)

        return voice

    def _generate_recognition_audio(self):
        raise NotImplementedError("this method must be overridden")

    def _recognize_short(self, timeout=360) -> [RecognizeResponse, None]:
        logger.debug("standard operation, timeout: %d", timeout)

        response: RecognizeResponse = self.client.recognize(
            config=self.recognition_config,
            audio=self.recognition_audio,
            timeout=timeout
        )

        return response

    def _recognize_long(self, timeout=360) -> [RecognizeResponse, None]:
        logger.debug("long running operation, timeout: %d", timeout)

        operation = self.client.long_running_recognize(
            config=self.recognition_config,
            audio=self.recognition_audio
        )

        response: RecognizeResponse = operation.result(timeout=timeout)

        return response

    def recognize(self, max_alternatives: [int, None] = None, *args, **kwargs) -> [List[SpeechRecognitionAlternative], None]:
        self._generate_recognition_audio()

        # noinspection PyTypeChecker
        self.recognition_config = RecognitionConfig(
            encoding=RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=self.hertz_rate,
            language_code=self.LANGUAGE,
            enable_automatic_punctuation=True,
            max_alternatives=max_alternatives,
            profanity_filter=False
        )

        if not self.short:
            logger.debug("using long running operation")
            response: RecognizeResponse = self._recognize_long(*args, **kwargs)
        else:
            logger.debug("using standard operation")
            response: RecognizeResponse = self._recognize_short(*args, **kwargs)

        if not response:
            logger.warning("no response")
            return
        else:
            logger.debug("response received")

        transcriptions = list()

        result: SpeechRecognitionResult
        for result in response.results:
            alternative: SpeechRecognitionAlternative
            for j, alternative in enumerate(result.alternatives):
                transcriptions.append(alternative)

        return transcriptions

    def cleanup(self):
        try:
            os.remove(self.file_path)
        except FileNotFoundError:
            pass


class VoiceMessageLocal(VoiceMessage):
    def _generate_recognition_audio(self):
        with io.open(self.file_path, "rb") as audio_file:
            # noinspection PyTypeChecker
            self.recognition_audio = RecognitionAudio(content=audio_file.read())


class VoiceMessageRemote(VoiceMessage):
    def __init__(self, *args, bucket_name, **kwargs):
        super(VoiceMessageRemote, self).__init__(*args, **kwargs)

        self.bucket_name = bucket_name
        self.storage_client: StorageClient = storage_client
        self.bucket = None
        self.gcs_uri = "gs://{}/{}".format(self.bucket_name, self.file_name)   # we can already compose it here

    def _generate_recognition_audio(self):
        # noinspection PyTypeChecker
        self.recognition_audio = RecognitionAudio(uri=self.gcs_uri)

    def _upload_blob(self):
        blob = self.bucket.blob(self.file_path)

        blob.upload_from_filename(self.file_path)

    def _delete_blob(self):
        blob = self.bucket.blob(self.file_path)

        blob.delete()

    def recognize(self, *args, **kwargs) -> List[SpeechRecognitionAlternative]:
        # all the network stuff goes here, not in __init__
        self.bucket = self.storage_client.get_bucket(self.bucket_name)
        self._upload_blob()

        return super(VoiceMessageRemote, self).recognize(*args, **kwargs)

    def cleanup(self, remove_from_bucket=True):
        if remove_from_bucket:
            self._delete_blob()

        super(VoiceMessageRemote, self).cleanup()
