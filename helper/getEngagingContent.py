import json
import os
import re
import time
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"

SYSTEM_INSTRUCTION = """
You are an expert short-form video editor.

Select highlight clips from transcript segments. Each output clip must use only
timestamps that appear in the transcript, must have start < end, and should be
a complete engaging idea. Prefer 90-180 seconds. Return only valid JSON.
"""


def _load_segments(transcript_file: str) -> list[dict[str, Any]]:
    with open(transcript_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict) and "segments" in data:
        data = data["segments"]

    segments = []
    for segment in data:
        if "start" not in segment or "end" not in segment:
            continue
        segments.append({
            "start": float(segment["start"]),
            "end": float(segment["end"]),
            "text": str(segment.get("text", "")).strip(),
        })

    return segments


def _chunk_segments(
    segments: list[dict[str, Any]],
    max_segments: int,
) -> list[list[dict[str, Any]]]:
    if max_segments <= 0:
        return [segments]
    return [
        segments[index:index + max_segments]
        for index in range(0, len(segments), max_segments)
    ]


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"Groq response did not contain a JSON array: {text}")
    parsed = json.loads(match.group())
    if not isinstance(parsed, list):
        raise ValueError("Groq response JSON was not an array")
    return parsed


def _groq_chat(
    messages: list[dict[str, str]],
    model_name: str,
    retries: int = 4,
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to .env.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(retries):
        response = httpx.post(GROQ_URL, headers=headers, json=payload, timeout=120)
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        wait_seconds = min(30, 2 ** attempt)
        time.sleep(wait_seconds)

    response.raise_for_status()
    raise RuntimeError("Groq request failed after retries")


def _normalize_highlights(
    highlights: list[dict[str, Any]],
    minimum_duration: float = 90,
) -> list[dict[str, Any]]:
    normalized = []
    seen = set()

    for clip in highlights:
        try:
            start = float(clip["start"])
            end = float(clip["end"])
        except (KeyError, TypeError, ValueError):
            continue

        if end <= start or (end - start) < minimum_duration:
            continue

        key = (round(start, 2), round(end, 2))
        if key in seen:
            continue
        seen.add(key)

        normalized.append({
            "start": start,
            "end": end,
            "reason": str(clip.get("reason", "")).strip(),
            "content": str(clip.get("content", "")).strip(),
        })

    return sorted(normalized, key=lambda item: item["start"])


def _candidate_prompt(segments: list[dict[str, Any]]) -> str:
    return json.dumps({
        "task": "Return JSON object with key clips containing 1-3 highlight clips from these transcript segments.",
        "rules": [
            "Each clip must be at least 90 seconds.",
            "Prefer 90 to 180 seconds.",
            "Use only provided timestamps.",
            "Do not include explanation outside JSON.",
        ],
        "segments": segments,
    }, ensure_ascii=False)


def generate_highlights(
    transcript_file: str,
    output_file: str = "highlights.json",
    model_name: str = DEFAULT_MODEL,
    max_segments: int = 80,
) -> list[dict[str, Any]]:
    segments = _load_segments(transcript_file)
    if not segments:
        raise ValueError(f"No transcript segments found in {transcript_file}")

    candidates = []
    for chunk in _chunk_segments(segments, max_segments=max_segments):
        content = _groq_chat(
            model_name=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": _candidate_prompt(chunk)},
            ],
        )
        parsed = json.loads(content)
        candidates.extend(parsed["clips"] if "clips" in parsed else _extract_json_array(content))

    final_prompt = json.dumps({
        "task": "Pick the top 3-5 clips from these candidates. Return JSON object with key clips.",
        "candidates": _normalize_highlights(candidates, minimum_duration=60),
    }, ensure_ascii=False)

    final_content = _groq_chat(
        model_name=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": final_prompt},
        ],
    )
    parsed_final = json.loads(final_content)
    final_clips = (
        parsed_final["clips"]
        if "clips" in parsed_final
        else _extract_json_array(final_content)
    )
    highlights = _normalize_highlights(final_clips, minimum_duration=90)

    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(highlights, file, indent=2, ensure_ascii=False)

    return highlights


if __name__ == "__main__":
    print(generate_highlights("output4.json", "highlights.json"))
