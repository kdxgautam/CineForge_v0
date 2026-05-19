# ClipGenerator Backend

Welcome to the backend of the **ClipGenerator** pipeline. This project focuses on automatically downloading videos, extracting meaningful/engaging segments, analyzing active speakers using a designated Active Speaker Detection (ASD) model, and cutting the video into short, engaging clips.

## Project Structure

- **main.py**: The entry point for the backend logic.
- **helper/**: Scripts for processing different stages of generating clips.
  - `ytdownload.py` & `gdrivedownload.py`: For downloading source videos.
  - `extractAudio.py` & `extractSubtitles.py`: For separating streams from the main video.
  - `subtitleParser.py` & `getEngagingContent.py`: For parsing text and determining highlight-worthy timestamps.
  - `run_asd.py` & `asdHelper.py`: Wrappers and helpers to run the LR-ASD (Active Speaker Detection) model against video clips.
  - `cutClips.py`, `normalizeVideo.py`, `video_process.py`: Handles cutting clips with ffmpeg/other video processors and normalizing outputs.
- **external/LR-ASD**: A sub-module for the **LR-ASD** (Low-Resolution Active Speaker Detection) model. Contains its own requirements and scripts.
- **outputs/** & **clips/** & **downloads/**: Directories for saving generated artifacts.
- **requirements.txt / pyproject.toml**: Python dependencies.

## Setup & Installation

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Prepare the active speaker detection model:
   - Make sure you check the `external/LR-ASD/README.md` for specific model weights (like `sfd_face.pth` and `pretrain_AVA.model`) required in `external/LR-ASD/weight/` and `external/LR-ASD/model/faceDetector/s3fd/`.

## Architecture Overview

1. **Ingestion**: Videos are fetched via `ytdownload` or `gdrivedownload`.
2. **Analysis**: 
   - Audio and subtitles are extracted.
   - Using NLP or heuristics in `getEngagingContent.py`, engaging segments are identified.
3. **Active Speaker Detection**: 
   - For chosen segments, the frames are passed to `LR-ASD` to identify who is speaking.
4. **Rendering**:
   - The final video clips are cut (`cutClips.py`), processed, normalized, and stored in the `outputs/final/` folder.

## Usage

Run the main file to execute the pipeline:

```bash
python main.py
```
*(Check main.py or add arguments as configured for your specific pipeline execution.)*