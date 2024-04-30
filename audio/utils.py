import time
import wave

import pyaudio


def play_audio(filename: str, stop_signal, start_time_conn):
    # Load file.
    wf = wave.open(filename, 'rb')

    # Instantiate PyAudio.
    p = pyaudio.PyAudio()

    # Open stream.
    stream = p.open(
        format=p.get_format_from_width(wf.getsampwidth()),
        channels=wf.getnchannels(),
        rate=wf.getframerate(),
        output=True,
    )

    # Read data.
    start_time_conn.put(time.time())
    data = wf.readframes(1024)
    while len(data) > 0:
        stream.write(data)
        data = wf.readframes(1024)
        if stop_signal.poll():
            print(stop_signal.recv())
            break

    # Stop stream.
    stream.stop_stream()
    stream.close()

    # Close PyAudio.
    p.terminate()