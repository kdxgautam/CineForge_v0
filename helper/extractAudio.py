
import subprocess
import os

def extract_audio(input_video, output_audio=None, format="mp3"):
    """
    Extract audio from video using FFmpeg

    Args:
        input_video (str): path to input video
        output_audio (str): optional output path
        format (str): mp3 / wav

    Returns:
        str: path to extracted audio file
    """

    if output_audio is None:
        base = os.path.splitext(input_video)[0]
        output_audio = f"{base}.{format}"

    command = [
        "ffmpeg",
        "-i", input_video,
        "-vn",                 # no video
        "-acodec", "libmp3lame" if format == "mp3" else "pcm_s16le",
        "-ar", "16000",        # sample rate (good for Whisper)
        "-ac", "1",            # mono audio
        output_audio
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return output_audio
