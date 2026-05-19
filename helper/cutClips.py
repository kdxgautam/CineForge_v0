def cut_clip(
    input_video: str,
    start: float,
    end: float,
    output_video: str
):

    command = [
        "ffmpeg",
        "-y",

        # fast seeking
        "-ss", str(start),

        "-i", input_video,

        "-to", str(end - start),

        # stream copy
        "-c", "copy",

        output_video
    ]

    subprocess.run(
        command,
        check=True
    )

    print(
        f"\n✅ Clip saved:\n{output_video}"
    )