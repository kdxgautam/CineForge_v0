import importlib.util
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def ok(message: str) -> None:
    print(f"[ok] {message}")


def warn(message: str) -> None:
    print(f"[warn] {message}")


def fail(message: str) -> None:
    print(f"[fail] {message}")


def check_file(path: Path, label: str, required: bool = True) -> bool:
    if path.exists():
        ok(label)
        return True
    if required:
        fail(f"{label} missing: {path}")
    else:
        warn(f"{label} missing: {path}")
    return False


def main() -> int:
    load_dotenv(ROOT / ".env")
    failures = 0

    for path, label in [
        (ROOT / "pyproject.toml", "pyproject.toml"),
        (ROOT / "uv.lock", "uv.lock"),
        (ROOT / ".env.example", ".env.example"),
        (ROOT / "app.py", "FastAPI app.py"),
    ]:
        failures += not check_file(path, label)

    if os.getenv("GROQ_API_KEY"):
        ok("GROQ_API_KEY is set")
    else:
        fail("GROQ_API_KEY is not set in .env")
        failures += 1

    if os.getenv("HF_TOKEN"):
        ok("HF_TOKEN is set")
    else:
        warn("HF_TOKEN is not set; WhisperX diarization/private model access may fail")

    if shutil.which("ffmpeg"):
        ok("ffmpeg is available")
    else:
        fail("ffmpeg is not available on PATH")
        failures += 1

    lr_asd = ROOT / "external" / "LR-ASD"
    check_file(lr_asd / "Columbia_test.py", "LR-ASD Columbia_test.py", required=False)
    check_file(lr_asd / "ASD.py", "LR-ASD ASD.py", required=False)
    check_file(lr_asd / "weight" / "pretrain_AVA.model", "LR-ASD AVA weights", required=False)
    check_file(lr_asd / "model" / "faceDetector" / "s3fd" / "sfd_face.pth", "LR-ASD S3FD weights", required=False)

    for module in ["fastapi", "httpx", "torch", "cv2", "yt_dlp"]:
        if importlib.util.find_spec(module):
            ok(f"Python module {module}")
        else:
            fail(f"Python module {module} is missing")
            failures += 1

    try:
        import torch

        ok(f"torch imported; cuda={torch.cuda.is_available()}")
    except Exception as exc:
        fail(f"torch import failed: {exc}")
        failures += 1

    try:
        from helper.whisperx_compat import load_whisperx

        load_whisperx()
        ok("whisperx imported via compatibility loader")
    except Exception as exc:
        fail(f"whisperx import failed: {exc}")
        failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
