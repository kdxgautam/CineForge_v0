import json
import os
import re
import time
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"

SYSTEM_INSTRUCTION = """
You are an expert short-form video editor.

Select highlight clips from transcript segments. Each output clip must use only
timestamps that appear in the transcript, must have start < end, and should be
a complete engaging idea. Prefer 90-180 seconds. If nothing is exceptional,
choose the strongest available complete idea anyway. Return only valid JSON.
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
        raise ValueError(f"LLM response did not contain a JSON array: {text}")
    parsed = json.loads(match.group())
    if not isinstance(parsed, list):
        raise ValueError("LLM response JSON was not an array")
    return parsed


def _env_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _llm_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()
    if provider != "auto":
        return provider
    if _env_value("OPENROUTER_API_KEY", "openrouter_api_key"):
        return "openrouter"
    return "groq"


def _llm_config(model_name: str | None = None) -> tuple[str, str, str, dict[str, str]]:
    provider = _llm_provider()

    if provider == "openrouter":
        api_key = _env_value("OPENROUTER_API_KEY", "openrouter_api_key")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to .env.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://127.0.0.1:8000"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "CineForge"),
        }
        model = model_name or os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        return provider, OPENROUTER_URL, model, headers

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to .env.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        model = model_name or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        return provider, GROQ_URL, model, headers

    raise RuntimeError("LLM_PROVIDER must be 'auto', 'openrouter', or 'groq'.")


def _chat_completion(
    messages: list[dict[str, str]],
    model_name: str | None = None,
    retries: int = 4,
) -> str:
    provider, url, model, headers = _llm_config(model_name)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(retries):
        response = httpx.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code == 400 and payload.get("response_format"):
            payload.pop("response_format", None)
            response = httpx.post(url, headers=headers, json=payload, timeout=120)

        if response.status_code != 429:
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        retry_after = response.headers.get("retry-after")
        wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else min(60, 2 ** attempt)
        time.sleep(wait_seconds)

    response.raise_for_status()
    raise RuntimeError(f"{provider} request failed after retries")


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


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _fallback_highlight(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable = [segment for segment in segments if segment["end"] > segment["start"]]
    if not usable:
        return []

    first_start = usable[0]["start"]
    last_end = usable[-1]["end"]
    total_duration = last_end - first_start
    if total_duration <= 0:
        return []

    min_duration = min(90.0, total_duration)
    target_duration = min(150.0, max(min_duration, total_duration))
    best: dict[str, Any] | None = None
    best_score = -1.0

    for start_index, start_segment in enumerate(usable):
        start = start_segment["start"]
        texts = []
        end = start_segment["end"]

        for segment in usable[start_index:]:
            end = segment["end"]
            texts.append(segment["text"])
            duration = end - start

            if duration < min_duration:
                continue

            text = " ".join(part for part in texts if part).strip()
            density = _word_count(text) / max(duration, 1.0)
            duration_fit = 1.0 / (1.0 + abs(duration - target_duration) / target_duration)
            score = density + duration_fit

            if score > best_score:
                best_score = score
                best = {
                    "start": start,
                    "end": end,
                    "reason": "Fallback clip selected because the LLM returned no valid highlights.",
                    "content": text[:500],
                }

            if duration >= target_duration:
                break

    if best:
        return [best]

    text = " ".join(segment["text"] for segment in usable if segment["text"]).strip()
    return [{
        "start": first_start,
        "end": last_end,
        "reason": "Fallback clip selected from the full transcript.",
        "content": text[:500],
    }]


def _candidate_prompt(segments: list[dict[str, Any]]) -> str:
    return json.dumps({
        "task": "Return JSON object with key clips containing 1-3 highlight clips from these transcript segments.",
        "rules": [
            "Each clip must be at least 90 seconds.",
            "Prefer 90 to 180 seconds.",
            "Always return at least 1 clip, even if the content is only moderately engaging.",
            "Use only provided timestamps.",
            "Do not include explanation outside JSON.",
        ],
        "segments": segments,
    }, ensure_ascii=False)


def generate_highlights(
    transcript_file: str,
    output_file: str = "highlights.json",
    model_name: str | None = None,
    max_segments: int = 80,
) -> list[dict[str, Any]]:
    segments = _load_segments(transcript_file)
    if not segments:
        raise ValueError(f"No transcript segments found in {transcript_file}")

    candidates = []
    for chunk in _chunk_segments(segments, max_segments=max_segments):
        content = _chat_completion(
            model_name=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": _candidate_prompt(chunk)},
            ],
        )
        parsed = json.loads(content)
        candidates.extend(parsed["clips"] if "clips" in parsed else _extract_json_array(content))

    normalized_candidates = _normalize_highlights(candidates, minimum_duration=60)
    if not normalized_candidates:
        highlights = _fallback_highlight(segments)
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(highlights, file, indent=2, ensure_ascii=False)
        return highlights

    final_prompt = json.dumps({
        "task": "Pick the top 3-5 clips from these candidates. Return JSON object with key clips. Always return at least 1 clip.",
        "candidates": normalized_candidates,
    }, ensure_ascii=False)

    final_content = _chat_completion(
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
    if not highlights:
        highlights = _fallback_highlight(segments)

    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(highlights, file, indent=2, ensure_ascii=False)

    return highlights


if __name__ == "__main__":
    print(generate_highlights("output4.json", "highlights.json"))
