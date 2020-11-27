import io
import os
import logging
import struct
import time
from typing import List, Tuple, Union

# noinspection PyPackageRequirements
from google.cloud.storage import Client as StorageClient
# noinspection PyPackageRequirements
from google.cloud.speech import (
    SpeechClient,
    RecognitionConfig,
    RecognitionAudio,
    RecognizeResponse,
    SpeechRecognitionResult,
    SpeechRecognitionAlternative,
    LongRunningRecognizeRequest,
    LongRunningRecognizeResponse
)
# from google.longrunning.operations_proto import Operation
# noinspection PyPackageRequirements
from telegram import Message

from google.clients import speech_client
from google.clients import storage_client
from .exceptions import UnsupportedFormat

logger = logging.getLogger(__name__)


class VoiceMessage:
    LANGUAGE = "it-IT"
    # opus hertz rate should always be 48000, but for some reasons google's api sometimes work only when 16000 hertz is
    # specified. This probably depends on the device the voice message has been recorded from, although ffmpeg
    # always says the hertz rate is 48000
    # https://stackoverflow.com/a/39186779/13350541
    SAMPLE_RATE_ANDROID = 16000
    SAMPLE_RATE_IOS = 48000
    SAMPLE_RATE_DESKTOP = 48000
    SAMPLE_RATE_MAC = 48000

    def __init__(
            self,
            file_name: str,
            duration: int,
            download_dir='downloads',
            force_sample_rate: [int, None] = None,
            max_alternatives: [int, None] = None
    ):
        if duration is None:
            raise ValueError("the voice message duration must be provided")
        elif max_alternatives is not None:
            raise NotImplementedError

        self.file_name = file_name
        self.file_path = os.path.join(download_dir, self.file_name)
        self.duration = duration
        self.short = True
        self.sample_rate = None
        self.forced_sample_rate = force_sample_rate
        self.client: SpeechClient = speech_client
        self.max_alternatives = max_alternatives
        self.recognition_audio: [RecognitionAudio, None] = None
        self.recognition_config: [RecognitionConfig, None] = None
        self.parsed_header_data = {}

        if self.duration > 59:
            self.short = False

    @classmethod
    def from_message(cls, message: Message, download=True, *args, **kwargs):
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

        if download:
            logger.debug("downloading voice message to %s", voice.file_path)
            telegram_file = message.voice.get_file()
            telegram_file.download(voice.file_path)

        return voice

    @staticmethod
    def pretty_sample_rate(value):
        if value % 1000 == 0:
            return f"{int(value / 1000)}kHz"
        else:
            return f"{value / 1000}kHz"

    @property
    def sample_rate_str(self):
        if self.sample_rate is None:
            raise ValueError("hertz rate is None")

        return self.pretty_sample_rate(self.sample_rate)

    @property
    def forced_sample_rate_str(self):
        if self.forced_sample_rate is None:
            return None

        return self.pretty_sample_rate(self.forced_sample_rate)

    def _generate_recognition_audio(self):
        raise NotImplementedError("this method must be overridden")

    def _recognize_short(self, timeout=360) -> Tuple[Union[str, None], Union[float, None]]:
        logger.debug("standard operation, timeout: %d", timeout)

        response: RecognizeResponse = self.client.recognize(
            config=self.recognition_config,
            audio=self.recognition_audio,
            timeout=timeout
        )

        if not response:
            logger.warning("no response")
            return None, None

        result: SpeechRecognitionResult
        for result in response.results:
            best_alternative: SpeechRecognitionAlternative = result.alternatives[0]
            return best_alternative.transcript, round(best_alternative.confidence, 2)

    def _recognize_long(self, timeout=360) -> Tuple[Union[str, None], Union[float, None]]:
        logger.debug("long running operation, timeout: %d", timeout)

        operation = self.client.long_running_recognize(
            config=self.recognition_config,
            audio=self.recognition_audio
        )

        """print(dir(operation))

        for i in range(12):
            time.sleep(2)
            print(operation_current_status.metadata, operation_current_status.done)
            if operation_current_status.done is True:
                break"""

        response: LongRunningRecognizeResponse = operation.result(timeout=timeout)

        if not response:
            logger.warning("no response")
            return None, None

        transcript = ""
        confidences = []

        result: SpeechRecognitionResult
        for result in response.results:
            best_alternative: SpeechRecognitionAlternative = result.alternatives[0]
            transcript += " " + best_alternative.transcript
            confidences.append(best_alternative.confidence)

        average_confidence = sum(confidences) / len(confidences)

        return transcript.strip(), round(average_confidence, 2)

    def _read_sample_rate(self):
        # for this to work, we need this line:
        # https://github.com/devsnd/tinytag/blob/9c7bd666f753d0eb6eb8573c5574510ed366641e/tinytag/tinytag.py#L802
        # to be set to "sr" (and not to a costant)
        # file_metadata = TinyTag.get(self.file_path)
        # self.hertz_rate = file_metadata.samplerate
        raise NotImplementedError

    def parse_sample_rate(self):
        with io.open(self.file_path, "rb") as fh:
            header_data = fh.read(27)
            header = struct.unpack('<4sBBqIIiB', header_data)
            # https://xiph.org/ogg/doc/framing.html
            oggs, version, flags, pos, serial, pageseq, crc, segments = header
            # print(oggs, version, flags, pos, serial, pageseq, crc, segments)
            # self._max_samplenum = max(self._max_samplenum, pos)

            if oggs != b'OggS' or version != 0:
                raise UnsupportedFormat('not a valid ogg file (not OggS or version != 0)')

            segsizes = struct.unpack('B' * segments, fh.read(segments))

            packet = b""  # also called "first page"

            total = 0
            for segsize in segsizes:  # read all segments
                total += segsize
                if total < 255:  # less than 255 bytes means end of page
                    packet = fh.read(total)
                    break

            # packet[0:8] -> first 64 bits (8 bytes)
            if packet[0:8] != b"OpusHead":
                raise ValueError("packet must be OpusHead")

            walker = io.BytesIO(packet)

            # https://www.videolan.org/developers/vlc/modules/codec/opus_header.c
            # https://mf4.xiph.org/jenkins/view/opus/job/opusfile-unix/ws/doc/html/structOpusHead.html
            walker.seek(8, os.SEEK_CUR)  # jump over header name's 8 bytes
            # - version number (8 bits, 1 byte -> "B")
            # - Channels C (8 bits, 1 byte -> "B")
            # - Pre - skip (16 bits, 2 bytes -> "H")
            # - Sampling rate (32 bits, 4 bytes -> "I")
            # - Gain in dB (16 bits, S7 .8, 2 bytes -> "H")
            # - Mapping type (8 bits, 1 byte -> "B")
            # total: 11 bytes
            (version, channels, pre_skip, sample_rate, gain, mapping_type) = struct.unpack("<BBHIHB", walker.read(11))

            if (version & 0xF0) != 0:
                raise ValueError("only major version 0 supported")

            self.sample_rate = sample_rate
            self.parsed_header_data = {
                "version": version,
                "channels": channels,
                "pre_skip": pre_skip,
                "gain": gain,
                "mapping_type": mapping_type
            }

    def recognize(self, max_alternatives: [int, None] = None, punctuation: bool = True, *args, **kwargs) -> Tuple[Union[str, None], Union[float, None]]:
        self._generate_recognition_audio()

        if not self.sample_rate:
            self.parse_sample_rate()

        self.parse_sample_rate()
        logger.debug("file sample rate: %d (forced: %s)", self.sample_rate, self.forced_sample_rate)

        # noinspection PyTypeChecker
        self.recognition_config = RecognitionConfig(
            encoding=RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=self.forced_sample_rate if self.forced_sample_rate else self.sample_rate,
            language_code=self.LANGUAGE,
            enable_automatic_punctuation=punctuation,
            # max_alternatives=max_alternatives,
            profanity_filter=False
        )

        if not self.short:
            return self._recognize_long(*args, **kwargs)
        else:
            return self._recognize_short(*args, **kwargs)

    def cleanup(self):
        logger.debug("cleaning up file: %s", self.file_path)

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

    def recognize(self, *args, **kwargs):
        # all the network stuff goes here, not in __init__
        self.bucket = self.storage_client.get_bucket(self.bucket_name)
        self._upload_blob()

        return super(VoiceMessageRemote, self).recognize(*args, **kwargs)

    def cleanup(self, remove_from_bucket=True):
        if remove_from_bucket:
            self._delete_blob()

        super(VoiceMessageRemote, self).cleanup()
