import re
import json

def srt_to_json(file_path):
    cleaned = []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for seg in data:
        cleaned.append({
            "text": seg["text"].strip(),
            "start": seg["start"],
            "end": seg["end"],
            "speaker": seg.get("speaker", "unknown")
        })

    return cleaned





