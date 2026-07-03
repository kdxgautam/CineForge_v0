import subprocess
import os
from pathlib import Path


def _escape_subtitles_path(path: str) -> str:
    resolved = str(Path(path).resolve())
    return resolved.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def burn_subtitles(
    input_video: str,
    input_srt: str,
    output_video: str
):
    output_dir = os.path.dirname(output_video)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)


    command = [
        "ffmpeg",
        "-y",

        "-i", input_video,

        "-vf",
        f"subtitles='{_escape_subtitles_path(input_srt)}'",

        "-c:v", "libx264",

        "-preset", "fast",

        "-crf", "18",

        "-c:a", "copy",

        output_video
    ]

    subprocess.run(
        command,
        check=True
    )

    print(
        f"\n✅ Subtitle video saved:\n{output_video}"
    )
