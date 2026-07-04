import json
import os
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from starlette.staticfiles import StaticFiles

from helper.burn import build_subtitle_style, burn_subtitles
from helper.cutClips import generate_clips
from helper.extractAudio import extract_audio
from helper.getEngagingContent import generate_highlights
from helper.run_all_asd import run_asd_on_clips
from helper.srt import generate_clip_srt_from_full_transcript
from helper.transcribe import generate_word_level_transcript
from helper.video_process import process_all_clips
from helper.ytdownload import download_youtube_video


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
JOBS_DIR = ROOT_DIR / "jobs"
FRONTEND_DIR = ROOT_DIR / "frontend"

app = FastAPI(title="CineForge Backend", version="0.1.0")
app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")
app.mount("/media", StaticFiles(directory=JOBS_DIR, check_dir=False), name="media")

PIPELINE_STAGES = [
    "queued",
    "download_youtube_video",
    "extract_audio",
    "transcribe_full_video",
    "generate_highlights",
    "generate_clips",
    "run_asd_on_clips",
    "process_all_clips",
    "generate_srts_from_transcript",
    "burn_subtitles_on_all_clips",
    "complete",
]


class ProcessVideoRequest(BaseModel):
    url: str
    quality: str = "1080"
    model_size: str = Field(default_factory=lambda: os.getenv("DEFAULT_WHISPER_MODEL", "small"))
    device: Literal["cpu", "cuda"] = Field(
        default_factory=lambda: os.getenv("DEFAULT_TRANSCRIBE_DEVICE", "cpu")
    )
    batch_size: int = 2
    compute_type: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_WHISPER_COMPUTE_TYPE", "int8")
    )
    max_segments: int = 80
    words_per_subtitle: int = 3
    subtitle_font_size: int = Field(default=11, ge=6, le=28)
    subtitle_margin_v: int = Field(default=35, ge=0, le=240)


def create_job() -> dict[str, Path | str]:
    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    paths = {
        "id": job_id,
        "root": job_dir,
        "downloads": job_dir / "downloads",
        "clips": job_dir / "clips",
        "asd": job_dir / "outputs" / "asd",
        "processed": job_dir / "outputs" / "processed",
        "transcripts": job_dir / "outputs" / "transcripts",
        "srt": job_dir / "outputs" / "srt",
        "final": job_dir / "outputs" / "final",
        "status": job_dir / "status.json",
    }
    for value in paths.values():
        if isinstance(value, Path) and value.suffix == "":
            value.mkdir(parents=True, exist_ok=True)
    return paths


def stage_progress(stage: str) -> dict[str, Any]:
    try:
        index = PIPELINE_STAGES.index(stage)
    except ValueError:
        index = 0

    return {
        "stage_index": index,
        "stage_count": len(PIPELINE_STAGES) - 1,
        "progress": round(index / (len(PIPELINE_STAGES) - 1), 3),
        "stages": PIPELINE_STAGES,
    }


def write_status(
    paths: dict[str, Any],
    stage: str,
    status: str = "running",
    **extra: Any,
) -> None:
    payload = {
        "job_id": paths["id"],
        "status": status,
        "stage": stage,
        **stage_progress(stage),
        **extra,
    }
    with open(paths["status"], "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, default=str)


def transcribe_full_video(request: ProcessVideoRequest, video_path: Path, output_path: Path):
    return generate_word_level_transcript(
        video_path=str(video_path),
        output_json=str(output_path),
        model_size=request.model_size,
        device=request.device,
        batch_size=request.batch_size,
        compute_type=request.compute_type,
    )


def generate_srts_from_transcript(
    paths: dict[str, Any],
    full_transcript: Path,
    highlights: list[dict[str, Any]],
    words_per_subtitle: int,
) -> list[str]:
    generated = []
    processed_dir = Path(paths["processed"])
    srt_dir = Path(paths["srt"])
    clips_by_name = {f"clip_{index}": highlight for index, highlight in enumerate(highlights)}

    for clip_path in sorted(processed_dir.glob("*.mp4")):
        highlight = clips_by_name.get(clip_path.stem)
        if not highlight:
            raise RuntimeError(f"Could not find highlight timing for {clip_path.name}")

        srt_path = srt_dir / f"{clip_path.stem}.srt"
        generate_clip_srt_from_full_transcript(
            transcript_json=str(full_transcript),
            output_srt=str(srt_path),
            clip_start=float(highlight["start"]),
            clip_end=float(highlight["end"]),
            words_per_subtitle=words_per_subtitle,
        )
        generated.append(str(srt_path))

    return generated


def burn_subtitles_on_all_clips(
    paths: dict[str, Any],
    subtitle_style: str,
    status_extra: dict[str, Any] | None = None,
) -> list[str]:
    final_files = []
    processed_clips = sorted(Path(paths["processed"]).glob("*.mp4"))
    srt_dir = Path(paths["srt"])
    final_dir = Path(paths["final"])
    status_extra = status_extra or {}

    write_status(
        paths,
        "burn_subtitles_on_all_clips",
        final_clips=final_files,
        final_clip_count=0,
        total_final_clips=len(processed_clips),
        **status_extra,
    )

    for clip_path in processed_clips:
        srt_path = srt_dir / f"{clip_path.stem}.srt"
        output_path = final_dir / f"{clip_path.stem}_subtitled.mp4"
        burn_subtitles(
            input_video=str(clip_path),
            input_srt=str(srt_path),
            output_video=str(output_path),
            subtitle_style=subtitle_style,
        )
        final_files.append(str(output_path))
        write_status(
            paths,
            "burn_subtitles_on_all_clips",
            final_clips=final_files,
            final_clip_count=len(final_files),
            total_final_clips=len(processed_clips),
            current_final_clip=str(output_path),
            **status_extra,
        )

    return final_files


@app.get("/")
def healthcheck():
    return {"status": "ok", "service": "cineforge-backend"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    status_path = JOBS_DIR / job_id / "status.json"
    if not status_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    with open(status_path, "r", encoding="utf-8") as file:
        return json.load(file)


def run_process_video(request: ProcessVideoRequest, paths: dict[str, Any]) -> dict[str, Any]:
    write_status(paths, "download_youtube_video")
    video_path = Path(download_youtube_video(
        url=request.url,
        output_dir=str(paths["downloads"]),
        quality=request.quality,
    ))

    write_status(paths, "extract_audio", video_path=video_path)
    audio_path = extract_audio(str(video_path), str(Path(paths["downloads"]) / "audio.mp3"))

    full_transcript = Path(paths["root"]) / "transcript.json"
    write_status(paths, "transcribe_full_video", audio_path=audio_path)
    transcribe_full_video(request, video_path, full_transcript)

    highlights_path = Path(paths["root"]) / "highlights.json"
    write_status(paths, "generate_highlights")
    highlights = generate_highlights(
        transcript_file=str(full_transcript),
        output_file=str(highlights_path),
        max_segments=request.max_segments,
    )

    write_status(paths, "generate_clips", highlights=highlights)
    clips = generate_clips(
        input_video=str(video_path),
        highlights_file=str(highlights_path),
        output_dir=str(paths["clips"]),
    )

    write_status(paths, "run_asd_on_clips", clips=clips)
    asd_results = run_asd_on_clips(
        clips_dir=str(paths["clips"]),
        output_base_dir=str(paths["asd"]),
    )
    failed_asd = [result for result in asd_results if result["status"] != "success"]
    if failed_asd:
        raise RuntimeError(f"LR-ASD failed for clips: {failed_asd}")

    write_status(paths, "process_all_clips")
    processed = process_all_clips(
        clips_dir=str(paths["clips"]),
        asd_outputs_dir=str(paths["asd"]),
        final_output_dir=str(paths["processed"]),
    )

    write_status(paths, "generate_srts_from_transcript")
    srts = generate_srts_from_transcript(
        paths=paths,
        full_transcript=full_transcript,
        highlights=highlights,
        words_per_subtitle=request.words_per_subtitle,
    )

    subtitle_style = build_subtitle_style(
        font_size=request.subtitle_font_size,
        margin_v=request.subtitle_margin_v,
    )

    write_status(
        paths,
        "burn_subtitles_on_all_clips",
        subtitle_font_size=request.subtitle_font_size,
        subtitle_margin_v=request.subtitle_margin_v,
    )
    final_clips = burn_subtitles_on_all_clips(
        paths,
        subtitle_style,
        status_extra={
            "subtitle_font_size": request.subtitle_font_size,
            "subtitle_margin_v": request.subtitle_margin_v,
        },
    )

    result = {
        "job_id": paths["id"],
        "status": "complete",
        "video_path": str(video_path),
        "full_transcript": str(full_transcript),
        "highlights": highlights,
        "clips": clips,
        "asd": asd_results,
        "processed": processed,
        "subtitle_source": "full_transcript",
        "subtitle_style": {
            "font_size": request.subtitle_font_size,
            "margin_v": request.subtitle_margin_v,
        },
        "srts": srts,
        "final_clips": final_clips,
    }
    write_status(paths, "complete", status="complete", result=result)
    return result


def run_process_video_job(request: ProcessVideoRequest, paths: dict[str, Any]) -> None:
    try:
        run_process_video(request, paths)
    except Exception as exc:
        write_status(paths, "failed", status="failed", error=str(exc))


@app.post("/process-video")
def process_video(request: ProcessVideoRequest):
    paths = create_job()

    try:
        return run_process_video(request, paths)
    except Exception as exc:
        write_status(paths, "failed", status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/process-video-async")
def process_video_async(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    paths = create_job()
    write_status(paths, "queued", status="queued")
    background_tasks.add_task(run_process_video_job, request, paths)
    return {
        "job_id": paths["id"],
        "status": "queued",
        "stage": "queued",
        "status_url": f"/jobs/{paths['id']}",
        **stage_progress("queued"),
    }
