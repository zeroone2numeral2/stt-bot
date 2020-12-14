import datetime
import logging
import time
from typing import Tuple, Union

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram import Update, Message, MAX_MESSAGE_LENGTH, ParseMode

from bot.database.models.chat import Chat
from bot.database.models.user import User
from bot.database.models.transcription_request import TranscriptionRequest
from bot.database.queries import transcription_request
from google.speechtotext import VoiceMessageLocal
from google.speechtotext import VoiceMessageRemote
from google.speechtotext.exceptions import UnsupportedFormat
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)

SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")  # https://stackoverflow.com/a/24392215


class RecogResult:
    def __init__(self, message_to_edit=None, raw_transcript=None, confidence=None, elapsed=None, transcription=None):
        self.message_to_edit: [Message, None] = message_to_edit
        self._raw_transcript: [str, None] = raw_transcript
        self.transcript_slices = []
        self.confidence: [float, None] = confidence
        self.elapsed: [float, None] = elapsed
        self.transcript: [str, None] = transcription
        self.success = False

        if self._raw_transcript:
            self.generate_transcript_slices()

    @property
    def raw_transcript(self):
        return self._raw_transcript

    @raw_transcript.setter
    def raw_transcript(self, value: str):
        self._raw_transcript = value

        self.generate_transcript_slices()

    @property
    def confidence_subscript(self):
        return str(self.confidence).translate(SUBSCRIPT)

    @property
    def elapsed_subscript(self):
        return str(self.elapsed).translate(SUBSCRIPT)

    def generate_transcript_slices(self, sep=" ", safe_threshold=100, max_len=None):
        """Slice the full transcript into smaller one, that fit into a message

        :param sep: what to use to separate words
        :param safe_threshold: how many characters we should keep for markdown tags and other characters sent with the transcription
        :param max_len: what should be the max allowed length of a text message
        :return:
        """

        if not max_len:
            max_len = MAX_MESSAGE_LENGTH

        if safe_threshold >= max_len:
            raise ValueError("marging_threshold can not be bigger than max_len")

        logger.debug("len: %d; max_len: %d; marging_threshold: %d", len(self._raw_transcript), max_len, safe_threshold)

        candidate_text = ""
        words_list = self._raw_transcript.split()
        number_of_words = len(words_list)
        for i, word in enumerate(words_list):
            if len(candidate_text + sep + word) > (max_len - safe_threshold):
                logger.debug("message build at word count %d (text len: %d)", i, len(candidate_text))
                self.transcript_slices.append(candidate_text)
                candidate_text = word
            else:
                candidate_text += sep + word

            if i + 1 == number_of_words:
                # if it's the last word: append what we have built until now
                logger.debug("last word reached: appending what's left (%d characters)", len(candidate_text))
                self.transcript_slices.append(candidate_text)

        return self.transcript_slices

    @property
    def full_transcription_words_count(self):
        return len(self._raw_transcript.split())

    @property
    def transcription_slices_words_count(self):
        return sum([len(t.split()) for t in self.transcript_slices])


def recognize_voice(
        voice: [VoiceMessageLocal, VoiceMessageRemote],
        update: Update,
        session: Session,
        punctuation: [bool, None] = None,
) -> RecogResult:
    if punctuation is None:
        punctuation = config.google.punctuation

    if voice.short:
        text = "<i>Inizio trascrizione...</i>"
    else:
        avg_response_time = transcription_request.estimated_duration(session, voice.duration)
        text = "<i>Inizio trascrizione... Per i vocali >1 minuto potrebbe volerci un po' di più</i>"
        if avg_response_time:
            text = text.replace("</i>", f" (stimato: {round(avg_response_time, 1)}\")</i>")

    message_to_edit = update.message.reply_html(text, disable_notification=True, quote=True)

    result = RecogResult(message_to_edit=message_to_edit)

    start = datetime.datetime.now()

    request = TranscriptionRequest(audio_duration=voice.duration)

    try:
        raw_transcript, confidence = voice.recognize(punctuation=punctuation)
        result.success = True
    except UnsupportedFormat:
        logger.error("unsupported format while transcribing voice %s", voice.file_path)
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        return result
        # return message_to_edit, None
    except Exception as e:
        logger.error("unknown exception while transcribing voice %s: ", voice.file_path, str(e))
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        return result
        # return message_to_edit, None

    result.raw_transcript = raw_transcript
    result.confidence = confidence

    end = datetime.datetime.now()
    elapsed = round((end - start).total_seconds(), 1)
    result.elapsed = elapsed

    if not raw_transcript:
        logger.warning("request for voice message \"%s\" returned empty response (file not deleted)", voice.file_path)
        if not config.misc.keep_files_on_error:
            voice.cleanup()

        return result
        # return message_to_edit, None

    request.successful(elapsed, sample_rate=voice.sample_rate)
    session.add(request)  # add the request instance to the session only on success

    # print('\n'.join([f"{round(a.confidence, 2)}: {a.transcript}" for a in result]))

    result.transcript = f"\"<i>{raw_transcript}</i>\" {result.confidence_subscript} {result.elapsed_subscript}"

    if config.misc.remove_downloaded_files:
        voice.cleanup()

    return result
    # return message_to_edit, transcription


def ignore_message_group(
        session: Session,
        user: User,
        chat: Chat,
        message: Message
):
    is_forward_from_user = utilities.is_forward_from_user(message)
    if chat.ignore_tos:
        return False, "chat is set to ignore tos"
    elif not is_forward_from_user and not user.tos_accepted:
        return True, "non-forwarded and sender did not accept tos"
    elif is_forward_from_user and utilities.user_hidden_account(message):
        return False, "forwarded message: original sender with hidden account"
    elif is_forward_from_user and message.forward_from.is_bot:
        return False, "forwarded message: original sender is a bot"
    elif is_forward_from_user:
        # forwarded message from an user who did not decide to hide their account
        user: [User, None] = session.query(User).filter(User.user_id == message.forward_from.id).one_or_none()
        if not user or not user.tos_accepted:
            return True, "forwarded message: original sender not in db or did not accept tos"
        else:
            return False, "forwarded message: original sender accepted tos"

    return False, "sender accepted tos"


def send_transcription(result: RecogResult) -> int:
    if len(result.transcript) < MAX_MESSAGE_LENGTH:
        result.message_to_edit.edit_text(
            result.transcript,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )
        return 1

    # 1: build the messages to send
    start_by_first_message = '"<i>'
    start_by = '"<i>...'
    end_by = '...</i>" <b>[{}/{}]</b>'
    end_by_last_message = '</i>" <b>[{i}/{tot}] {conf} {elapsed}"</b>'
    additional_characters = len(start_by) + len(end_by)
    result.generate_transcript_slices(safe_threshold=additional_characters, max_len=MAX_MESSAGE_LENGTH / 2)

    if result.full_transcription_words_count != result.transcription_slices_words_count:
        error_desc = "words count mismatch (full: %d, split: %d)" % (result.full_transcription_words_count, result.transcription_slices_words_count)
        logger.error(error_desc)
        logger.error("transcription: %s", result.raw_transcript)
        raise ValueError(error_desc)

    # 2: send the messages
    total_texts = len(result.transcript_slices)
    logger.debug("log transcriptions: %d texts to send", total_texts)
    reply_to = result.message_to_edit
    for i, text in enumerate(result.transcript_slices):
        text = text.strip()  # remove white spaced at the beginning/end

        if i == 0:
            # we edit the "Transcribing voice message..." message
            text_to_send = start_by_first_message + text + end_by.format(i + 1, total_texts)
            result.message_to_edit.edit_text(
                text_to_send,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
        elif i + 1 == total_texts:
            # we are sending the last message
            text_to_send = start_by + text + end_by_last_message.format(
                i=i + 1,
                tot=total_texts,
                conf=result.confidence_subscript,
                elapsed=result.elapsed_subscript
            )
            reply_to.reply_html(text_to_send, disable_web_page_preview=True, quote=True)
        else:
            # save the last message we sent so we can reply to it the next cicle
            text_to_send = start_by + text + end_by.format(i + 1, total_texts)
            reply_to = reply_to.reply_html(text_to_send, disable_web_page_preview=True, quote=True)

        time.sleep(1)

    return total_texts
