import subprocess
import os


# -----------------------------------
# NORMALIZE VIDEO
# -----------------------------------
def normalize_video(
    input_video: str,
    output_video: str
):

    command = [
        "ffmpeg",
        "-y",

        "-i", input_video,

        # -----------------------------------
        # VIDEO
        # -----------------------------------
        "-c:v", "libx264",

        "-preset", "medium",

        "-crf", "18",

        # target fps
        "-r", "30",

        # modern CFR
        "-fps_mode", "cfr",

        # compatibility
        "-pix_fmt", "yuv420p",

        # -----------------------------------
        # AUDIO
        # -----------------------------------
        "-c:a", "aac",

        "-b:a", "192k",

        # -----------------------------------
        # FASTSTART
        # -----------------------------------
        "-movflags",
        "+faststart",

        output_video
    ]

    subprocess.run(
        command,
        check=True
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

