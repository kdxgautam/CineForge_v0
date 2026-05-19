import subprocess
import os


# -----------------------------------
# NORMALIZE VIDEO
# -----------------------------------
def normalize_video(
    input_video: str,
    output_video: str
):
    """
    Normalize video for stable AI processing.

    Converts to:
    - H264
    - AAC
    - 30 FPS CFR
    - yuv420p
    """

    if not os.path.exists(input_video):

        raise FileNotFoundError(
            f"\n❌ Input video not found:\n{input_video}"
        )

    command = [
        "ffmpeg",
        "-y",

        "-i", input_video,

        # -----------------------------------
        # VIDEO
        # -----------------------------------
        "-c:v", "libx264",

        "-preset", "fast",

        "-crf", "18",

        # constant framerate
        "-r", "30",

        "-vsync", "cfr",

        # maximum compatibility
        "-pix_fmt", "yuv420p",

        # -----------------------------------
        # AUDIO
        # -----------------------------------
        "-c:a", "aac",

        # -----------------------------------
        # OUTPUT
        # -----------------------------------
        output_video
    ]

    print("\n🎥 Normalizing video...")

    subprocess.run(
        command,
        check=True
    )

    print(
        f"\n✅ Normalized video saved:\n{output_video}"
    )


# -----------------------------------
# CUT SINGLE CLIP
# -----------------------------------
def cut_clip(
    input_video: str,
    start: float,
    end: float,
    output_video: str
):
    """
    Cut clip from normalized video.
    """

    if not os.path.exists(input_video):

        raise FileNotFoundError(
            f"\n❌ Input video not found:\n{input_video}"
        )

    command = [
        "ffmpeg",
        "-y",

        # -----------------------------------
        # INPUT
        # -----------------------------------
        "-i", input_video,

        # -----------------------------------
        # TIMESTAMPS
        # -----------------------------------
        "-ss", str(start),

        "-to", str(end),

        # -----------------------------------
        # VIDEO
        # -----------------------------------
        "-c:v", "libx264",

        "-preset", "fast",

        "-crf", "18",

        # -----------------------------------
        # AUDIO
        # -----------------------------------
        "-c:a", "aac",

        # -----------------------------------
        # OUTPUT
        # -----------------------------------
        output_video
    ]

    print(
        f"\n🎬 Cutting clip:"
        f"\nStart: {start}"
        f"\nEnd: {end}"
    )

    subprocess.run(
        command,
        check=True
    )

    print(
        f"\n✅ Clip saved:\n{output_video}"
    )


# -----------------------------------
# EXAMPLE USAGE
# -----------------------------------
if __name__ == "__main__":

    # -----------------------------------
    # STEP 1:
    # NORMALIZE VIDEO
    # -----------------------------------
    normalize_video(
        input_video="downloads/video.mp4",
        output_video="downloads/normalized.mp4"
    )

    # -----------------------------------
    # STEP 2:
    # CUT CLIP
    # -----------------------------------
    cut_clip(
        input_video="downloads/normalized.mp4",
        start=30,
        end=90,
        output_video="clips/clip_0.mp4"
    )