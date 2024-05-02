import math
import multiprocessing as mp
import os
import re
import time
from multiprocessing import Pipe, Process, Queue

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import demucs.api
from audio.pitch_detection import YIN_realtime_pitch_detection, pitch_detection, realtime_pitch_detection
from audio.utils import play_audio
from DataCrawler.youtube2MP3 import convertMP4toWAV, downloadYouTube


def download_song(url: str):
    # Download the song
    download_dir = "downloaded_songs"
    filename = downloadYouTube(url, download_dir)

    # Convert the song to wav
    file_path = os.path.join(download_dir, filename)
    convertMP4toWAV(file_path, download_dir)

    # Get the file_path of the downloaded song
    file_path = os.path.join(download_dir, filename.split(".")[0] + ".wav")

    return file_path


def sep_audio(input_path, output_path):
    # Check the output path
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Load the model
    separator = demucs.api.Separator()

    # Load the audio
    wav = separator._load_audio(input_path)

    # Separate the audio
    _, separated = separator.separate_tensor(wav)
    for key in separated.keys():
        demucs.api.save_audio(separated[key], f'{key}.wav', samplerate=44100, clip='none')
        # Move the separated audio to the output path
        os.rename(f'{key}.wav', os.path.join(output_path, f'{key}.wav'))


def plot_process(stop_signal):
    # Plot the recorded pitch in `frequency_history`.
    if st.session_state.get('frequency_pred') is None:
        st.session_state['frequency_pred'] = Queue()
    with st.empty():
        while True:
            confidence, frequency = st.session_state['frequency_pred'].get()
            if len(st.session_state['frequency_history']) == 0:
                st.session_state['frequency_history'].append(frequency)
            else:
                if confidence > 0.5:
                    st.session_state['frequency_history'].append(frequency)
                else:
                    st.session_state['frequency_history'].append(st.session_state['frequency_history'][-1])
            st.line_chart(st.session_state['frequency_history'][-100:])
            if stop_signal.poll():
                print(stop_signal.recv())
                break


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    if st.session_state.get('stop_signal') is None:
        PARENT_CONN, CHILD_CONN = Pipe()
        st.session_state['stop_signal'] = PARENT_CONN
        st.session_state['child_conn'] = CHILD_CONN
    if st.session_state.get('stop_music') is None:
        PARENT_CONN, CHILD_CONN = Pipe()
        st.session_state['stop_music'] = PARENT_CONN
        st.session_state['music_child_conn'] = CHILD_CONN
    if st.session_state.get('frequency_pred') is None:
        st.session_state['frequency_pred'] = Queue()
    if st.session_state.get('frequency_history') is None:
        st.session_state['frequency_history'] = []
    if st.session_state.get('stop_plot') is None:
        PARENT_CONN, CHILD_CONN = Pipe()
        st.session_state['stop_plot'] = PARENT_CONN
        st.session_state['plot_child_conn'] = CHILD_CONN

    # Setting layout
    st.title("Pitch Detection")
    status_text = st.sidebar.empty()
    download_url = status_text.text_input("Enter the url to download the song", value="")
    status_placeholder = st.sidebar.empty()

    # Check if the url is valid
    if not re.match(r"https://www.youtube.com/watch\?v=[a-zA-Z0-9]+", download_url):
        st.sidebar.write("Invalid URL! Please enter a valid YouTube URL.")
    else:
        # Print the status
        status_placeholder.text("Downloading the song...")
        wav_file = download_song(download_url)
        status_placeholder.text("Downloaded the song successfully!")

        # Separate the audio
        status_placeholder.text("Separating the audio...")
        # Get filename.
        filename = os.path.basename(wav_file).split(".")[0]
        sep_audio(wav_file, f"separated_audio/{filename}")
        status_placeholder.text("Separated the audio successfully!")

        # Pitch detection
        status_placeholder.text("Detecting the pitch...")
        times, frequency, confidence, activation = pitch_detection(f"separated_audio/{filename}/vocals.wav")
        status_placeholder.text("Detected the pitch successfully!")
        # Save the pitch detection result
        pitch_detection_result = pd.DataFrame({"Time": times, "Frequency": frequency, "Confidence": confidence})
        if not os.path.exists("pitch_detection_results"):
            os.makedirs("pitch_detection_results")
        pitch_detection_result.to_csv(f"pitch_detection_results/{filename}.csv", index=False)

    # Select the pitch detection result file
    file_list = os.listdir("pitch_detection_results")
    selected_file = st.sidebar.selectbox("Select the pitch detection result file", file_list)

    # Select the music file
    music_list = os.listdir("downloaded_songs")
    selected_music = st.sidebar.selectbox("Select the music file", music_list)

    # Add a buttion to play the music
    if st.sidebar.button("Play"):
        status_placeholder.text("Playing the music...")
        # threading.Thread(target=play_audio, args=(f"downloaded_songs/{selected_music}",)).start()
        if st.session_state.get('detection_result') is None:
            st.session_state['detection_result'] = pd.read_csv(f"pitch_detection_results/{selected_file}")
            st.session_state['start_time_conn'] = Queue()
            st.session_state['pitch_history'] = [(0, 0.0)] * 50
        Process(
            target=play_audio, args=(
                f"downloaded_songs/{selected_music}",
                st.session_state['music_child_conn'],
                st.session_state['start_time_conn'],
            )
        ).start()
        while st.session_state['start_time_conn'].empty():
            pass
        st.session_state['start_time'] = st.session_state['start_time_conn'].get()
        status_placeholder.text("Played the music successfully!")
    if st.sidebar.button("Stop Music"):
        status_placeholder.text("Stop the music...")
        st.session_state['stop_music'].send('stop')
        status_placeholder.text("Stopped the music successfully!")
        st.session_state['detection_result'] = None

    # Add a buttion to start record
    if st.sidebar.button("Record"):
        st.session_state['frequency_pred'] = Queue()
        st.session_state['frequency_history'] = [(0, 0.0)] * 50
        # threading.Thread(target=realtime_pitch_detection, args=(STORE_PLACE, stop_signal)).start()
        # Process(
        #   target=YIN_realtime_pitch_detection, args=(
        #   st.session_state['frequency_pred'], st.session_state['child_conn'])).start()
        Process(
            target=realtime_pitch_detection, args=(
                st.session_state['frequency_pred'], st.session_state['child_conn']
            )
        ).start()
        # Process(target=plot_process, args=(st.session_state['stop_plot'],)).start()
    if st.sidebar.button("Stop Record"):
        st.session_state['stop_signal'].send('stop')
        # st.session_state['stop_plot'].send('stop')

    with st.empty():
        while True:
            record_color = 'rgba(255,0,0,1)'
            no_color = 'rgba(0,0,0,0)'
            song_color = 'rgba(0,255,0,1)'
            # Initialize scatter chart
            data = None
            if st.session_state.get('frequency_pred') is not None:
                confidence, frequency = st.session_state['frequency_pred'].get()
                st.session_state['frequency_history'].append((confidence, frequency))
                st.session_state['frequency_history'] = st.session_state['frequency_history'][-50:]
                data = pd.DataFrame({
                    'x': [i for i in range(len(st.session_state['frequency_history']))],
                    'y': [i[1] for i in st.session_state['frequency_history']],
                    'color': [no_color if i[0] < 0.5 else record_color for i in st.session_state['frequency_history']]
                })

            if st.session_state.get('detection_result') is not None and st.session_state.get('start_time') is not None:
                current_time = time.time() - st.session_state['start_time']
                index = math.floor(current_time / 0.01)
                if index == 0:
                    index = 1
                window = st.session_state['detection_result'][
                    ['Confidence', 'Frequency']][max(0, index - 2): min(index + 2, index)]
                # Select the pitch which has the highest confidence.
                confidence = window['Confidence'].max()
                pitch = window.loc[window['Confidence'] == confidence, 'Frequency'].values[0]
                st.session_state['pitch_history'].append((confidence, pitch))
                st.session_state['pitch_history'] = st.session_state['pitch_history'][-50:]
                tmp_data = pd.DataFrame({
                    'x': [i for i in range(len(st.session_state['pitch_history']))],
                    'y': [i[1] for i in st.session_state['pitch_history']],
                    'color': [no_color if i[0] < 0.7 else song_color for i in st.session_state['pitch_history']]
                })
                if data is not None:
                    data = pd.concat([data, tmp_data])
                else:
                    data = tmp_data
            st.vega_lite_chart(data, {
                'mark': 'circle',
                'encoding': {
                    'x': {'field': 'x', 'type': 'quantitative'},
                    'y': {'field': 'y', 'type': 'quantitative', 'scale': {
                        'domain': [0, 500], 'clamp': True}, 'axis': {'tickCount': 6}},
                    'color': {'field': 'color', 'type': 'nominal', 'scale': None}
                },
                'width': 800,
                'height': 600
            })