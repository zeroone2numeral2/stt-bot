import io
import os
from typing import List

from google.cloud import storage
from google.cloud.speech import SpeechClient
from google.cloud.speech import RecognitionConfig
from google.cloud.speech import RecognitionAudio
from google.cloud.speech import RecognizeResponse
from google.cloud.speech import SpeechRecognitionResult
from google.cloud.speech import SpeechRecognitionAlternative


# bucket_name = 'speech-recognition-bot-storage'

speech_client = SpeechClient.from_service_account_json('./speech-recognition-bot-2e6b405bf854.json')
storage_client = storage.Client.from_service_account_json('./speech-recognition-bot-2e6b405bf854.json')


class VoiceMessage:
    LANGUAGE = "it-IT"
    OPUS_HERTZ_RATE = 48000

    def __init__(self, file_name, duration, max_alternatives=None):
        if duration is None:
            raise ValueError('the voice message duration must be provided')
        elif max_alternatives is not None:
            raise NotImplementedError

        self.file_name = file_name
        self.file_path = os.path.join('voices', self.file_name)
        self.duration = duration
        self.client = speech_client
        self.max_alternatives = max_alternatives
        self.recognition_audio: [RecognitionAudio, None] = None
        self.recognition_config: [RecognitionConfig, None] = None

    def _generate_audio(self):
        raise NotImplementedError('this method must be overridden')

    def _recognize_short(self, timeout=360) -> [RecognizeResponse, None]:
        response: RecognizeResponse = self.client.recognize(
            config=self.recognition_config,
            audio=self.recognition_audio,
            timeout=timeout
        )

        return response

    def _recognize_long(self, timeout=360) -> [RecognizeResponse, None]:
        operation = self.client.long_running_recognize(
            config=self.recognition_config,
            audio=self.recognition_audio
        )

        response: RecognizeResponse = operation.result(timeout=timeout)

        return response

    def recognize(self, *args, **kwargs) -> List[SpeechRecognitionAlternative]:
        self._generate_audio()

        # noinspection PyTypeChecker
        self.recognition_config = RecognitionConfig(
            encoding=RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=self.OPUS_HERTZ_RATE,
            language_code=self.LANGUAGE,
            enable_automatic_punctuation=True,
            # max_alternatives=1,
            profanity_filter=False
        )

        if self.duration > 59:
            response: RecognizeResponse = self._recognize_long(*args, **kwargs)
        else:
            response: RecognizeResponse = self._recognize_short(*args, **kwargs)

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
    def _generate_audio(self):
        with io.open(self.file_path, "rb") as audio_file:
            # noinspection PyTypeChecker
            self.recognition_audio = RecognitionAudio(content=audio_file.read())


class VoiceMessageRemote(VoiceMessage):
    def __init__(self, *args, bucket_name, **kwargs):
        super(VoiceMessageRemote, self).__init__(*args, **kwargs)

        self.bucket_name = bucket_name
        self.storage_client = storage_client
        self.bucket = None
        self.gcs_uri = None

    def _generate_audio(self):
        self.recognition_audio = RecognitionAudio(uri=self.gcs_uri)

    def _upload_blob(self):
        blob = self.bucket.blob(self.file_name)

        blob.upload_from_filename(self.file_name)
        self.gcs_uri = 'gs://{}/{}'.format(self.bucket_name, self.file_name)

    def _delete_blob(self):
        blob = self.bucket.blob(self.file_name)

        blob.delete()

    def recognize(self, *args, **kwargs) -> List[SpeechRecognitionAlternative]:
        # all the network stuff goes here, not in __init__
        self.bucket = self.storage_client.get_bucket(self.bucket_name)
        self._upload_blob()

        return super(VoiceMessageRemote, self).recognize(*args, **kwargs)

    def cleanup(self):
        self._delete_blob()
        super(VoiceMessageRemote, self).cleanup()


