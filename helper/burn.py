import subprocess
import os
from pathlib import Path


DEFAULT_SUBTITLE_STYLE = (
    "FontName=DejaVu Sans,"
    "Fontsize=11,"
    "Bold=1,"
    "PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&HAA000000,"
    "BorderStyle=1,"
    "Outline=1.2,"
    "Shadow=0,"
    "Alignment=2,"
    "MarginV=35"
)


def build_subtitle_style(
    font_size: int = 11,
    margin_v: int = 35,
) -> str:
    font_size = max(6, min(28, int(font_size)))
    margin_v = max(0, min(240, int(margin_v)))

    return (
        "FontName=DejaVu Sans,"
        f"Fontsize={font_size},"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&HAA000000,"
        "BorderStyle=1,"
        "Outline=1.2,"
        "Shadow=0,"
        "Alignment=2,"
        f"MarginV={margin_v}"
    )


def _escape_subtitles_path(path: str) -> str:
    resolved = str(Path(path).resolve())
    return resolved.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def burn_subtitles(
    input_video: str,
    input_srt: str,
    output_video: str,
    subtitle_style: str = DEFAULT_SUBTITLE_STYLE,
):
    output_dir = os.path.dirname(output_video)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)


    command = [
        "ffmpeg",
        "-y",

        "-i", input_video,

        "-vf",
        f"subtitles='{_escape_subtitles_path(input_srt)}':force_style='{subtitle_style}'",

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
