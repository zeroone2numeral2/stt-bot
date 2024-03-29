import io
import os
import logging
import re
import struct
import time
from typing import List, Tuple, Union, Optional

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
from telegram import Message, Voice, TelegramError, Audio
from telegram.error import BadRequest

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
    OPUS_SAMPLE_RATE_ANDROID = 16000
    OPUS_SAMPLE_RATE_IOS = 48000
    OPUS_SAMPLE_RATE_DESKTOP = 48000
    OPUS_SAMPLE_RATE_MAC = 48000

    def __init__(
            self,
            file_name: str,
            duration: int,
            download_dir='downloads',
            force_sample_rate: Optional[int] = None,
            max_alternatives: Optional[int] = None,
            audio_encoding: Optional[RecognitionConfig.AudioEncoding] = None
    ):
        if duration is None:
            raise ValueError("the voice message duration must be provided")
        elif max_alternatives is not None:
            raise NotImplementedError

        self.file_name = file_name
        self.file_path = os.path.join(download_dir, self.file_name)
        self.duration = duration
        self.audio_encoding = audio_encoding if audio_encoding else RecognitionConfig.AudioEncoding.OGG_OPUS
        self.short = True
        self.sample_rate = None
        self.forced_sample_rate = force_sample_rate
        self.client: SpeechClient = speech_client
        self.max_alternatives = max_alternatives
        self.recognition_audio: Optional[RecognitionAudio] = None
        self.recognition_config: Optional[RecognitionConfig] = None
        self.parsed_header_data = {}

        if self.duration > 59:
            self.short = False

    @staticmethod
    def download_voice(voice: [Voice, Audio], file_path: str, retries: int = 3):
        logger.debug("downloading voice message to %s", file_path)

        while retries > 0:
            try:
                telegram_file = voice.get_file()
                telegram_file.download(file_path)
                retries = 0
            except (BadRequest, TelegramError) as e:
                if "temporarily unavailable" in e.message.lower():
                    logger.warning("downloading voice %s raised error: %s", voice.file_id, e.message)
                    time.sleep(2)
                    retries -= 1
                else:
                    raise

    @classmethod
    def from_message(cls, message: Message, download=True, *args, **kwargs):
        if not message.voice and not message.audio:
            raise AttributeError("Message object must contain a voice message or an audio")

        telegram_voice = message.voice or message.audio

        if telegram_voice.duration is None:
            raise ValueError("message.Voice or message.Audio must contain its duration")

        ext = "ogg"
        if message.audio and message.audio.file_name and re.search(r".+\..+", message.audio.file_name):
            ext = message.audio.file_name.split(".")[-1]

        file_name = "{}_{}.{}".format(message.chat.id, message.message_id, ext)

        voice = cls(
            file_name=file_name,
            duration=telegram_voice.duration,
            *args,
            **kwargs
        )

        if download:
            cls.download_voice(telegram_voice, voice.file_path)

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

    @staticmethod
    def _refactor_response_result(response: Union[RecognizeResponse, LongRunningRecognizeResponse]) -> Tuple[str, float]:
        transcript = ""
        confidences = {}  # {confidence: words count}, if the transcription is returned as multiple results
        average_confidence = None  # if the transcription is returned as one result

        results_count = len(response.results)
        result: SpeechRecognitionResult
        for i, result in enumerate(response.results):
            best_alternative: SpeechRecognitionAlternative = result.alternatives[0]
            transcript += " " + best_alternative.transcript

            if results_count > 1:
                # if there is more than one result (each one with its own confidence), we
                # calculate the actual confidence based on the words count of the transcript result
                confidences[best_alternative.confidence] = len(best_alternative.transcript.split())  # words count
            else:
                # if there is just one result, directly use the best alternative's confidence
                average_confidence = best_alternative.confidence

            # this part is just for debug purposes
            alternative: SpeechRecognitionAlternative
            for j, alternative in enumerate(result.alternatives):
                logger.debug("result #%d alt #%d [%f]: %s", i, j, alternative.confidence, alternative.transcript)

        logger.debug("confidencies: %s", confidences)

        """longer way of calculatating it, but at least you go through the dict just once
        total_weighted_confidence = 0.0
        total_num_words = 0
        for confidence, num_words in confidences.items():
            total_weighted_confidence += confidence * num_words
            total_num_words += num_words

        average_confidence = total_weighted_confidence / total_num_words
        """

        if not average_confidence:
            # the request returned more than one result: we need to calculate the average confidence
            average_confidence = sum([conf * words for conf, words in confidences.items()]) / sum(confidences.values())

        return transcript.strip(), round(average_confidence, 2)

    def _recognize_short(self, timeout=360) -> Tuple[Optional[str], Optional[float]]:
        logger.debug("standard (short) operation, timeout: %d", timeout)

        response: RecognizeResponse = self.client.recognize(
            config=self.recognition_config,
            audio=self.recognition_audio,
            timeout=timeout
        )

        if not response:
            logger.warning("no response")
            return None, None

        return self._refactor_response_result(response)

    def _recognize_long(self, timeout=360) -> Tuple[Optional[str], Optional[float]]:
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

        return self._refactor_response_result(response)

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
                "sample_rate": sample_rate,
                "gain": gain,
                "mapping_type": mapping_type
            }

    def recognize(self, max_alternatives: Optional[int] = None, punctuation: bool = True, *args, **kwargs) -> Tuple[Optional[str], Optional[float]]:
        self._generate_recognition_audio()

        self.parse_sample_rate()
        logger.debug("file sample rate: %d (forced: %s)", self.sample_rate, self.forced_sample_rate)

        # noinspection PyTypeChecker
        self.recognition_config = RecognitionConfig(
            encoding=self.audio_encoding,
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
