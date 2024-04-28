import os

from moviepy.editor import AudioFileClip
from pytube import YouTube


def downloadYouTube(videourl: str, save_dir: str):
    try:
        print("Downloading from: " + videourl)
        # Download YouTube video as MP3 file.
        yt_obj = YouTube(str(videourl)).streams.filter(only_audio=True).first()
        output_file = yt_obj.download(save_dir)
        # Rename the file.
        # base, ext = os.path.splitext(output_file)
        # new_file = base + '.'
        # os.rename(output_file, new_file)
        print("Download completed: " + output_file)
        return output_file
    except Exception as e:
        print(e)
    return False


def ConvertMP4toMP3(mp4_file: str, save_dir: str):
    try:
        print("Converting to MP3: " + mp4_file)
        # Get the name of original video.
        base, ext = os.path.splitext(mp4_file)
        output_file = base + '.mp3'
        # Convert MP4 file to MP3 file.
        audio_clip = AudioFileClip(mp4_file)
        audio_clip.write_audiofile(
            os.path.join(save_dir, output_file),
            codec='libmp3lame',
        )
        audio_clip.close()
        print("Conversion completed: " + mp4_file)
        print("Saved to: " + save_dir)
        # Delete the original MP4 file.
        os.remove(mp4_file)
        return True
    except Exception as e:
        print(e)
    return False


def convertMP4toWAV(mp4_file: str, save_dir: str):
    try:
        print("Converting to WAV: " + mp4_file)
        # Get the name of original video.
        base, ext = os.path.splitext(mp4_file)
        output_file = base + '.wav'
        # Convert MP3 file to WAV file.
        audio_clip = AudioFileClip(mp4_file)
        audio_clip.write_audiofile(
            os.path.join(save_dir, output_file),
        )
        audio_clip.close()
        print("Conversion completed: " + mp4_file)
        print("Saved to: " + save_dir)
        # Delete the original MP4 file.
        os.remove(mp4_file)
        return True
    except Exception as e:
        print(e)
    return False