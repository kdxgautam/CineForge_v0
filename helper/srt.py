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


def _iter_transcript_cues(data):
    segments = data.get("segments", data) if isinstance(data, dict) else data

    for segment in segments:
        words = segment.get("words") or []
        if words:
            for word in words:
                if "start" in word and "end" in word:
                    yield {
                        "start": float(word["start"]),
                        "end": float(word["end"]),
                        "text": str(word.get("word", "")).strip(),
                        "unit": "word",
                    }
            continue

        if "start" in segment and "end" in segment:
            yield {
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "text": str(segment.get("text", "")).strip(),
                "unit": "segment",
            }


def generate_clip_srt_from_full_transcript(
    transcript_json: str,
    output_srt: str,
    clip_start: float,
    clip_end: float,
    words_per_subtitle: int = 3,
):
    with open(transcript_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    cues = []
    for cue in _iter_transcript_cues(data):
        start = max(cue["start"], clip_start)
        end = min(cue["end"], clip_end)
        text = cue["text"]

        if end <= clip_start or start >= clip_end or not text:
            continue

        cues.append({
            "start": start - clip_start,
            "end": end - clip_start,
            "text": text,
            "unit": cue["unit"],
        })

    output_dir = os.path.dirname(output_srt)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_srt, "w", encoding="utf-8") as srt_file:
        subtitle_index = 1
        index = 0

        while index < len(cues):
            chunk_size = words_per_subtitle if cues[index]["unit"] == "word" else 1
            chunk = cues[index:index + chunk_size]
            start_time = chunk[0]["start"]
            end_time = chunk[-1]["end"]
            text = " ".join(cue["text"] for cue in chunk)

            srt_file.write(f"{subtitle_index}\n")
            srt_file.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            srt_file.write(f"{text}\n\n")

            subtitle_index += 1
            index += chunk_size

    print(f"\n✅ Clip SRT saved from full transcript:\n{output_srt}")
    return output_srt
