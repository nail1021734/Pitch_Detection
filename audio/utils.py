import wave

import pyaudio


def play_audio(filename: str, stop_signal):
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