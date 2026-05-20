import subprocess


def burn_subtitles(
    input_video: str,
    input_srt: str,
    output_video: str
):

    command = [
        "ffmpeg",
        "-y",

        "-i", input_video,

        "-vf",
        f"subtitles={input_srt}",

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


burn_subtitles(
    input_video="outputs/final/clip_0.mp4",
    input_srt="outputs/srt/clip_0.srt",
    output_video="outputs/final/clip_0_1.mp4"
)