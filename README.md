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

If `uv` is not installed globally but Python 3.12 is available, you can
bootstrap it inside a local virtualenv:

```bash
python3.12 -m venv .venv
.venv/bin/pip install uv
.venv/bin/uv sync
```

If your environment cannot write to the default home cache directories, keep
the caches inside the project:

```bash
UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib uv sync
```

Use the same environment variables when running checks or the server:

```bash
UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib uv run python scripts/check_setup.py
UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib uv run uvicorn app:app --host 127.0.0.1 --port 8000
```

Edit `.env`:

```bash
GROQ_API_KEY=your_groq_api_key
HF_TOKEN=your_huggingface_token_if_needed
DEFAULT_TRANSCRIBE_DEVICE=cpu
DEFAULT_WHISPER_MODEL=small
DEFAULT_WHISPER_COMPUTE_TYPE=int8
```

The placeholder values in `.env.example` are not valid credentials. If
`/process-video` fails after transcription with a `401 Unauthorized` response
from `https://api.groq.com/openai/v1/chat/completions`, replace
`GROQ_API_KEY` with a real Groq key.

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

The LR-ASD checkout includes `weight/pretrain_AVA.model` in the upstream repo at
the time this setup was tested, but the S3FD face detector weight may still be
missing. If it is not present, download it from the ID used by LR-ASD:

```bash
cd external/LR-ASD
../../.venv/bin/uv run gdown --id 1KafnHz7ccT-3IyddBsL5yi2xGtxAKypt -O model/faceDetector/s3fd/sfd_face.pth
cd ../..
```

If your `uv` command is global rather than inside `.venv`, replace
`../../.venv/bin/uv` with `uv`.

If your LR-ASD checkout is the upstream version, apply the compatibility notes in:

```text
docs/LR_ASD_PATCHES.md
```

These patches include CUDA-to-CPU fallback changes and a NumPy compatibility
fix that is required with modern NumPy.

## Compatibility Fixes Found During Setup

These were not obvious from a fresh-clone happy path, but were required in the
tested local environment.

1. `uv` may be missing globally.

   Fix: create `.venv`, install `uv` into it, and use `.venv/bin/uv`.

2. Home cache directories may be read-only in sandboxed or managed shells.

   Symptom:

   ```text
   Could not create temporary file ... /home/.../.cache/uv
   ```

   Fix:

   ```bash
   UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib .venv/bin/uv sync
   ```

3. WhisperX import can fail because the bundled `ctranslate2` shared library
   requests an executable stack.

   Symptom:

   ```text
   whisperx import failed: libctranslate2-....so...: cannot enable executable stack as shared object requires
   ```

   Fix with `execstack` or `patchelf` if available. If neither is installed,
   clear the executable bit on the installed virtualenv library:

   ```bash
   .venv/bin/python -c "from pathlib import Path; import struct; p=next(Path('.venv/lib/python3.12/site-packages').glob('ctranslate2.libs/libctranslate2*.so*')); data=bytearray(p.read_bytes()); phoff=struct.unpack_from('<Q', data, 32)[0]; phentsize=struct.unpack_from('<H', data, 54)[0]; phnum=struct.unpack_from('<H', data, 56)[0]; changed=False
   for i in range(phnum):
       off=phoff+i*phentsize
       if struct.unpack_from('<I', data, off)[0] == 0x6474e551:
           flags=struct.unpack_from('<I', data, off+4)[0]
           struct.pack_into('<I', data, off+4, flags & ~1)
           changed=True
   if not changed: raise SystemExit('PT_GNU_STACK not found')
   p.write_bytes(data)"
   ```

   Verify:

   ```bash
   readelf -l .venv/lib/python3.12/site-packages/ctranslate2.libs/libctranslate2*.so* | grep GNU_STACK
   ```

   The stack flags should be `RW`, not `RWE`.

4. LR-ASD upstream can fail under modern NumPy because `np.int` was removed.

   Symptom:

   ```text
   AttributeError: module 'numpy' has no attribute 'int'
   ```

   Fix in `external/LR-ASD/model/faceDetector/s3fd/box_utils.py`:

   ```python
   return np.array(keep).astype(int)
   ```

5. Groq credentials are required before full `/process-video` can pass.

   Symptom:

   ```text
   Client error '401 Unauthorized' for url 'https://api.groq.com/openai/v1/chat/completions'
   ```

   Fix: put a real `GROQ_API_KEY` in `.env`. The setup checker only confirms
   that the variable is set, not that the key is valid.

## Check Setup

```bash
uv run python scripts/check_setup.py
```

This checks the env file, Groq key, ffmpeg, LR-ASD files, Python imports, Torch, CUDA visibility, and WhisperX import compatibility.

## One-Clip Smoke Test

If a full `/process-video` request fails before clips are generated, you can
test the downstream stages without calling Groq by creating one short highlight
from an existing downloaded video and transcript.

Example using an existing job:

```bash
JOB=jobs/<job_id>
mkdir -p "$JOB/debug_one_clip"
python -c "import json, pathlib; root=pathlib.Path('$JOB/debug_one_clip'); (root/'highlights.json').write_text(json.dumps([{'start': 8.685, 'end': 28.685, 'reason': 'debug window', 'content': 'one clip smoke test'}], indent=2), encoding='utf-8')"
```

Generate one clip:

```bash
UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib uv run python -c "from helper.cutClips import generate_clips; print(generate_clips('$JOB/downloads/video.mp4', '$JOB/debug_one_clip/highlights.json', '$JOB/debug_one_clip/clips'))"
```

Run LR-ASD only for that clip:

```bash
UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib uv run python -c "from helper.run_all_asd import run_asd_on_clips; print(run_asd_on_clips('$JOB/debug_one_clip/clips', '$JOB/debug_one_clip/outputs/asd'))"
```

Process to vertical video:

```bash
UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib uv run python -c "from helper.video_process import process_all_clips; print(process_all_clips('$JOB/debug_one_clip/clips', '$JOB/debug_one_clip/outputs/asd', '$JOB/debug_one_clip/outputs/processed'))"
```

Transcribe, create SRT, and burn subtitles for the one processed clip:

```bash
UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib uv run python -c "from helper.transcribe import generate_word_level_transcript; generate_word_level_transcript('$JOB/debug_one_clip/outputs/processed/clip_0.mp4', '$JOB/debug_one_clip/outputs/transcripts/clip_0.json', model_size='small', device='cpu', batch_size=2, compute_type='int8')"

UV_CACHE_DIR=.uv-cache MPLCONFIGDIR=.cache/matplotlib uv run python -c "from helper.srt import generate_srt; from helper.burn import burn_subtitles; generate_srt('$JOB/debug_one_clip/outputs/transcripts/clip_0.json', '$JOB/debug_one_clip/outputs/srt/clip_0.srt', words_per_subtitle=3); burn_subtitles('$JOB/debug_one_clip/outputs/processed/clip_0.mp4', '$JOB/debug_one_clip/outputs/srt/clip_0.srt', '$JOB/debug_one_clip/outputs/final/clip_0_subtitled.mp4')"
```

Expected final output:

```text
jobs/<job_id>/debug_one_clip/outputs/final/clip_0_subtitled.mp4
```

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
