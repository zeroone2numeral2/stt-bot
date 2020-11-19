### opus

opus-encoded files have an hertz rate of 48.000

### gcs

transcribing audio files longer than 1 minute requires `client.long_running_recognize()`. Google will ignore wrong hertz rate for shorter audios, but will return no results with long audios with wrong hertz rate
