from pydub import AudioSegment
open('downloads/23646077_12619.ogg')
audio_segment = AudioSegment.from_ogg('./downloads/23646077_12619.ogg')
audio_segment.export("testme.flac", format="flac")
