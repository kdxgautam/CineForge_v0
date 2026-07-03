import os
import json
import subprocess


# -----------------------------------
# CUT SINGLE CLIP
# -----------------------------------
# -----------------------------------
# CUT SINGLE CLIP
# -----------------------------------
def cut_clip(
    input_video: str,
    start: float,
    end: float,
    output_video: str
):

    # -----------------------------------
    # REMOVE OLD OUTPUT
    # -----------------------------------
    if os.path.exists(output_video):

        os.remove(output_video)

    # -----------------------------------
    # DURATION
    # -----------------------------------
    duration = end - start

    # -----------------------------------
    # FFMPEG COMMAND
    # -----------------------------------
    command = [
        "ffmpeg",
        "-y",

        # -----------------------------------
        # FAST SEEK
        # -----------------------------------
        "-ss", str(start),

        # -----------------------------------
        # INPUT
        # -----------------------------------
        "-i", input_video,

        # -----------------------------------
        # DURATION
        # -----------------------------------
        "-t", str(duration),

        # -----------------------------------
        # VIDEO CONVERSION
        # -----------------------------------
        "-c:v", "libx264",

        "-preset", "fast",

        "-crf", "18",

        # -----------------------------------
        # FORCE CFR
        # -----------------------------------
        "-r", "30",

        "-fps_mode", "cfr",

        # -----------------------------------
        # PIXEL FORMAT
        # -----------------------------------
        "-pix_fmt", "yuv420p",

        # -----------------------------------
        # AUDIO CONVERSION
        # -----------------------------------
        "-c:a", "aac",

        "-b:a", "192k",

        # -----------------------------------
        # FIX TIMESTAMPS
        # -----------------------------------
        "-avoid_negative_ts",
        "make_zero",

        # -----------------------------------
        # FASTSTART
        # -----------------------------------
        "-movflags",
        "+faststart",

        # -----------------------------------
        # OUTPUT
        # -----------------------------------
        output_video
    ]

    print("\n")
    print("=" * 50)

    print("🎬 Cutting + Converting Clip")

    print("=" * 50)

    print(f"\nInput: {input_video}")

    print(f"\nStart: {start}")

    print(f"\nEnd: {end}")

    print(f"\nOutput: {output_video}")

    # -----------------------------------
    # RUN FFMPEG
    # -----------------------------------
    subprocess.run(
        command,
        check=True
    )

    print(
        f"\n✅ Clip saved:\n{output_video}"
    )


# -----------------------------------
# GENERATE ALL CLIPS
# -----------------------------------
def generate_clips(
    input_video: str,
    highlights_file: str,
    output_dir: str = "clips"
):

    # -----------------------------------
    # VALIDATE INPUTS
    # -----------------------------------
    if not os.path.exists(input_video):

        raise FileNotFoundError(
            f"\n❌ Input video not found:\n{input_video}"
        )

    if not os.path.exists(highlights_file):

        raise FileNotFoundError(
            f"\n❌ Highlights file not found:\n{highlights_file}"
        )

    # -----------------------------------
    # CREATE OUTPUT DIR
    # -----------------------------------
    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # -----------------------------------
    # LOAD HIGHLIGHTS
    # -----------------------------------
    with open(
        highlights_file,
        "r",
        encoding="utf-8"
    ) as f:

        highlights = json.load(f)

    # -----------------------------------
    # GENERATE CLIPS
    # -----------------------------------
    generated = []

    for index, clip in enumerate(highlights):

        start = clip["start"]

        end = clip["end"]

        output_video = os.path.join(
            output_dir,
            f"clip_{index}.mp4"
        )

        print("\n")
        print("=" * 50)

        print(
            f"🎬 Generating clip "
            f"{index}"
        )

        print("=" * 50)

        print(f"\nStart: {start}")
        print(f"End: {end}")

        try:

            cut_clip(
                input_video=input_video,
                start=start,
                end=end,
                output_video=output_video
            )
            generated.append(output_video)

        except Exception as e:

            print(
                f"\n❌ Failed clip_{index}"
            )

            print(str(e))

    print("\n✅ All clips processed!")
    return generated


# -----------------------------------
# EXAMPLE USAGE
# -----------------------------------
if __name__ == "__main__":

    generate_clips(
        input_video="downloads/video.mp4",
        highlights_file="highlights.json",
        output_dir="clips"
    )
