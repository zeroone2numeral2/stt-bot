### opus

opus-encoded files have an hertz rate of 48.000

Getting infos about a file: `ffmpeg -i file.ogg`

Apparently google doesn't like vorbis-encoded ogg files: https://stackoverflow.com/a/50630951 (shouldn't be a problem since telegram voice messages are always opus-encoded)

### gcs

transcribing audio files longer than 1 minute requires `client.long_running_recognize()`. Google will ignore wrong hertz rate for shorter audios, but will return no results with long audios with wrong hertz rate
