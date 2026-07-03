import json
import os


# -----------------------------------
# FORMAT TIME
# -----------------------------------
def format_time(seconds):

    hours = int(seconds // 3600)

    minutes = int(
        (seconds % 3600) // 60
    )

    secs = int(seconds % 60)

    milliseconds = int(
        (seconds - int(seconds)) * 1000
    )

    return (
        f"{hours:02}:"
        f"{minutes:02}:"
        f"{secs:02},"
        f"{milliseconds:03}"
    )


# -----------------------------------
# GENERATE SRT
# -----------------------------------
def generate_srt(
    transcript_json: str,
    output_srt: str,
    words_per_subtitle: int = 3
):

    # -----------------------------------
    # LOAD JSON
    # -----------------------------------
    with open(
        transcript_json,
        "r"
    ) as f:

        data = json.load(f)

    # -----------------------------------
    # FLATTEN WORDS
    # -----------------------------------
    all_words = []

    for segment in data["segments"]:

        if "words" in segment:

            for word in segment["words"]:

                if (
                    "start" in word
                    and
                    "end" in word
                ):

                    all_words.append(word)

    # -----------------------------------
    # WRITE SRT
    # -----------------------------------
    output_dir = os.path.dirname(output_srt)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(
        output_srt,
        "w"
    ) as srt_file:

        subtitle_index = 1

        for i in range(
            0,
            len(all_words),
            words_per_subtitle
        ):

            chunk = all_words[
                i:i + words_per_subtitle
            ]

            if not chunk:
                continue

            start_time = chunk[0]["start"]

            end_time = chunk[-1]["end"]

            text = " ".join(
                word["word"]
                for word in chunk
            )

            srt_file.write(
                f"{subtitle_index}\n"
            )

            srt_file.write(
                f"{format_time(start_time)} --> "
                f"{format_time(end_time)}\n"
            )

            srt_file.write(
                f"{text}\n\n"
            )

            subtitle_index += 1

    print(
        f"\n✅ SRT saved:\n{output_srt}"
    )
