import io

import wave
from google.cloud import storage
from google.cloud.speech import SpeechClient
from google.cloud.speech import RecognitionAudio
from google.cloud.speech import RecognitionConfig
from google.cloud.speech import SpeechRecognitionAlternative
from google.cloud.speech import SpeechRecognitionResult
from google.cloud.speech import RecognizeResponse
# streaming
from google.cloud.speech import StreamingRecognizeRequest
from google.cloud.speech import StreamingRecognitionConfig

bucketname = 'speech-recognition-bot-storage'


def frame_rate_channel(audio_file_name):
    with wave.open(audio_file_name, "rb") as wave_file:
        frame_rate = wave_file.getframerate()
        channels = wave_file.getnchannels()
        return frame_rate,channels


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client.from_service_account_json('./speech-recognition-bot-2e6b405bf854.json')
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)


def delete_blob(bucket_name, blob_name):
    """Deletes a blob from the bucket."""
    storage_client = storage.Client.from_service_account_json('./speech-recognition-bot-2e6b405bf854.json')
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.delete()


def main_long(file_name, use_bucket=False):
    # https://cloud.google.com/speech-to-text/docs/async-recognize

    if use_bucket:
        gcs_file_name = 'current_voice.ogg'
        upload_blob(bucketname, file_name, gcs_file_name)
        gcs_uri = 'gs://' + bucketname + '/' + gcs_file_name

        audio = RecognitionAudio(uri=gcs_uri)
    else:
        with io.open(file_name, "rb") as audio_file:
            content = audio_file.read()
            audio = RecognitionAudio(content=content)

    client = SpeechClient.from_service_account_json('./speech-recognition-bot-2e6b405bf854.json')

    config = RecognitionConfig(
        encoding=RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=48000,
        language_code="it-IT",
        enable_automatic_punctuation=True,
        # max_alternatives=1,
        profanity_filter=False
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    print("Waiting for operation to complete...")
    response = operation.result(timeout=360)
    print('...ended')
    print(response)

    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    for result in response.results:
        # The first alternative is the most likely one for this portion.
        print("Transcript: {}".format(result.alternatives[0].transcript))
        print("Confidence: {}".format(result.alternatives[0].confidence))

    if use_bucket:
        delete_blob(bucketname, gcs_file_name)


def main(file_name):

    client = SpeechClient.from_service_account_json('./speech-recognition-bot-2e6b405bf854.json')

    with io.open(file_name, "rb") as audio_file:
        content = audio_file.read()
        audio = RecognitionAudio(content=content)

    config = RecognitionConfig(
        encoding=RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=48000,
        language_code="it-IT",
        enable_automatic_punctuation=True,
        # max_alternatives=1,
        profanity_filter=False
    )

    response: RecognizeResponse = client.recognize(config=config, audio=audio, timeout=300)
    print(response)

    result: SpeechRecognitionResult
    for i, result in enumerate(response.results):
        print("result " + str(i + 1))
        alternative: SpeechRecognitionAlternative
        for j, alternative in enumerate(result.alternatives):
            print('', "alternative {}".format(j + 1))
            print('', '', "transcript [{}]: {}".format(round(alternative.confidence, 2), alternative.transcript))


def main_streaming(file_name):

    client = SpeechClient.from_service_account_json('./speech-recognition-bot-2e6b405bf854.json')

    with io.open('downloads/io_16.ogg', "rb") as audio_file:
        content = audio_file.read()

    # In practice, stream should be a generator yielding chunks of audio data.
    stream = [content]

    requests = (
        StreamingRecognizeRequest(audio_content=chunk) for chunk in stream
    )

    config = RecognitionConfig(
        encoding=RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=48000,
        language_code="it-IT",
        enable_automatic_punctuation=True,
    )

    streaming_config = StreamingRecognitionConfig(config=config)

    # streaming_recognize returns a generator.
    responses = client.streaming_recognize(
        config=streaming_config,
        requests=requests,
    )

    for response in responses:
        # Once the transcription has settled, the first result will contain the
        # is_final result. The other results will be for subsequent portions of
        # the audio.
        for result in response.results:
            print("Finished: {}".format(result.is_final))
            print("Stability: {}".format(result.stability))
            alternatives = result.alternatives
            # The alternatives are ordered from most likely to least.
            for alternative in alternatives:
                print("Confidence: {}".format(alternative.confidence))
                print(u"Transcript: {}".format(alternative.transcript))


if __name__ == '__main__':
    main_long('downloads/gianni_107.ogg')
