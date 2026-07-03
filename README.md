# CineForge Backend

FastAPI backend for generating short vertical clips from long-form YouTube videos.

## Pipeline

```text
POST /process-video
download_youtube_video
extract_audio
transcribe_full_video
generate_highlights
generate_clips
run_asd_on_clips
process_all_clips
transcribe_processed_clips
generate_srts_from_transcript
burn_subtitles_on_all_clips
return final clips
```

## Requirements

- Python `3.12`, matching `.python-version`
- `uv`
- `ffmpeg` available on `PATH`
- `GROQ_API_KEY`
- Local LR-ASD checkout and weights in `external/LR-ASD`
- CUDA is optional but strongly recommended for WhisperX/LR-ASD

## Fresh Clone Setup

```bash
git clone <repo-url>
cd Backend
uv sync
cp .env.example .env
```

Edit `.env`:

```bash
GROQ_API_KEY=your_groq_api_key
HF_TOKEN=your_huggingface_token_if_needed
DEFAULT_TRANSCRIBE_DEVICE=cpu
DEFAULT_WHISPER_MODEL=small
DEFAULT_WHISPER_COMPUTE_TYPE=int8
```

For CUDA, verify it first:

```bash
uv run python -c "import torch; print(torch.cuda.is_available())"
```

Then use `"device": "cuda"` and usually `"compute_type": "float16"` in the API request.

## LR-ASD Setup

`external/LR-ASD/` is ignored by Git because the repo, weights, and demo outputs are large.

Clone LR-ASD after cloning this backend:

```bash
mkdir -p external
git clone https://github.com/Junhua-Liao/LR-ASD.git external/LR-ASD
```

The backend expects these files:

```text
external/LR-ASD/Columbia_test.py
external/LR-ASD/ASD.py
external/LR-ASD/weight/pretrain_AVA.model
external/LR-ASD/model/faceDetector/s3fd/sfd_face.pth
```

The model weights are not included in this backend repo. Add them to the paths above before running the full pipeline.

If your LR-ASD checkout is the upstream version, apply the compatibility notes in:

```text
docs/LR_ASD_PATCHES.md
```

## Check Setup

```bash
uv run python scripts/check_setup.py
```

This checks the env file, Groq key, ffmpeg, LR-ASD files, Python imports, Torch, CUDA visibility, and WhisperX import compatibility.

## Run Server

```bash
uv run python main.py
```

Or:

```bash
uv run uvicorn app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Test `/process-video`

CPU-safe request:

```json
{
  "url": "https://www.youtube.com/watch?v=ef3D5Ak1HP4&t=4s",
  "quality": "1080",
  "model_size": "small",
  "device": "cpu",
  "batch_size": 2,
  "compute_type": "int8",
  "max_segments": 80,
  "words_per_subtitle": 3
}
```

CUDA request:

```json
{
  "url": "https://www.youtube.com/watch?v=ef3D5Ak1HP4&t=4s",
  "quality": "1080",
  "model_size": "small",
  "device": "cuda",
  "batch_size": 2,
  "compute_type": "float16",
  "max_segments": 80,
  "words_per_subtitle": 3
}
```

`/process-video` is synchronous right now, so long videos can take a while. Job status is written to:

```text
jobs/<job_id>/status.json
```

The response includes the final subtitled clip paths when complete.

## YouTube Notes

If YouTube blocks downloads with bot/cookie errors, export browser cookies and configure yt-dlp locally. Do not commit cookies.

## GitHub Safety

Do commit:

```text
app.py
main.py
helper/
scripts/check_setup.py
docs/LR_ASD_PATCHES.md
.env.example
.gitignore
README.md
pyproject.toml
uv.lock
requirements.txt
```

Do not commit:

```text
.env
.venv/
.uv-cache/
.cache/
jobs/
downloads/
clips/
outputs/
external/
*.mp4
*.mp3
*.wav
*.srt
*.pckl
```

Before pushing:

```bash
git status --short
uv run python scripts/check_setup.py
```

Then stage the project files:

```bash
git add .gitignore README.md .env.example pyproject.toml uv.lock requirements.txt main.py app.py helper docs scripts/check_setup.py
git commit -m "Prepare backend for reproducible local setup"
git push
```
