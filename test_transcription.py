from google.speechtotext import VoiceMessageLocal
from google.cloud.speech import RecognitionConfig
from google.cloud.speech import SpeechClient

from config import config


def main():
    voice = VoiceMessageLocal(file_name="36s.raw", download_dir="tfiles", duration=36, force_sample_rate=16000, audio_encoding=RecognitionConfig.AudioEncoding.LINEAR16)
    result = voice.recognize(punctuation=False)
    print(result)


if __name__ == "__main__":
    main()
