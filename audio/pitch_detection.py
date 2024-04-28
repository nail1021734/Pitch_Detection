import os
import time
import wave
from datetime import datetime
from multiprocessing import Queue

import aubio
import crepe
import numpy as np
import pyaudio
from scipy.io import wavfile

FORMAT = pyaudio.paInt16  # 數據格式
CHANNELS = 1  # 單聲道
RATE = 16000  # 採樣率
CHUNK = 1024  # 每次讀取的數據塊大小


def YIN_realtime_pitch_detection(store_place: Queue, stop_signal):
    # Save the recorded audio
    frames = []

    # Instantiate PyAudio.
    p = pyaudio.PyAudio()

    # Open stream.
    stream = p.open(
        format=pyaudio.paFloat32,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    pitch_o = aubio.pitch("yin", CHUNK, CHUNK, 44100)
    pitch_o.set_unit("Hz")
    pitch_o.set_tolerance(0.8)

    while True:
        if stop_signal.poll():
            print(stop_signal.recv())
            break
        data = stream.read(CHUNK)
        frames.append(data)
        audio_data = np.frombuffer(data, dtype=np.float32)
        # start = time.time()
        pitch = pitch_o(audio_data)[0]
        # print(f"Time: {time.time() - start}")
        print(f"Pitch: {pitch}")

        # Store the pitch
        store_place.put((0.8, pitch))

    # Stop stream.
    stream.stop_stream()
    stream.close()

    # Close PyAudio.
    p.terminate()

    # Save the recorded audio
    if not os.path.exists("recorded_audio"):
        os.makedirs("recorded_audio")

    # Name the recorded audio file by time and date.
    now = datetime.now()
    dt_string = now.strftime("%Y%m%d%H%M%S")
    wf = wave.open(f"recorded_audio/{dt_string}.wav", 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()


def pitch_detection(audio_file: str):
    # Load the audio file
    sr, x = wavfile.read(audio_file)

    # Get the pitch
    time, frequency, confidence, activation = crepe.predict(x, sr, viterbi=True)

    return time, frequency, confidence, activation


def realtime_pitch_detection(store_place: Queue, stop_signal):
    # Save the recorded audio
    frames = []

    # Instantiate PyAudio.
    p = pyaudio.PyAudio()

    # Open stream.
    stream = p.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )
    # Read data.
    frequency = None
    confidence = None
    check = 2
    while True:
        if check != 2:
            check += 1
            data = stream.read(CHUNK)
            continue
        check = 0
        if stop_signal.poll():
            print(stop_signal.recv())
            break
        data = stream.read(CHUNK)
        frames.append(data)
        audio_data = np.frombuffer(data, dtype=np.int16)
        start = time.time()
        _, frequency, confidence, _ = crepe.predict(
            audio_data, RATE, viterbi=False, verbose=0, model_capacity="full", step_size=10)
        print(f"Time: {time.time() - start}")

        # print(f"Frequency: {sum(frequency)/len(frequency)}, Confidence: {sum(confidence)/len(confidence)}")

        # Store the pitch
        store_place.put((sum(confidence) / len(confidence), sum(frequency) / len(frequency)))

    # Stop stream.
    stream.stop_stream()
    stream.close()

    # Close PyAudio.
    p.terminate()

    # Save the recorded audio
    if not os.path.exists("recorded_audio"):
        os.makedirs("recorded_audio")

    # Name the recorded audio file by time and date.
    now = datetime.now()
    dt_string = now.strftime("%Y%m%d%H%M%S")
    wf = wave.open(f"recorded_audio/{dt_string}.wav", 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()