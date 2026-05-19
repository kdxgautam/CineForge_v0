import os
import subprocess
from yt_dlp import YoutubeDL


def download_youtube_video(
    url: str,
    output_dir: str = "downloads",
    quality: str = "best"
):
    """
    Download YouTube video + audio separately and merge them.

    Args:
        url: YouTube video URL
        output_dir: Folder to save files
        quality:
            "best" -> highest quality
            "1080" -> 1080p
            "720"  -> 720p
            etc.
    """

    os.makedirs(output_dir, exist_ok=True)

    # ---------------------------
    # Select video format
    # ---------------------------
    if quality == "best":
        video_format = "bestvideo"
    else:
        video_format = (
            f"bestvideo[height<={quality}]"
        )

    ydl_opts = {
        "format": f"{video_format}+bestaudio/best",
        "outtmpl": f"{output_dir}/video.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # Download video + audio separately
        ydl.download([url])

        print("\nDownload + merge complete.\n")


# Example usage
download_youtube_video(
    url="https://www.youtube.com/watch?v=ef3D5Ak1HP4",
    quality="1080"  # or "best"
)