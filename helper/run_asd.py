import os
import sys
import shutil
import subprocess

from pathlib import Path

from .runtime import runtime_env


# -----------------------------------
# PATHS
# -----------------------------------
CURRENT_DIR = Path(__file__).resolve().parent

BACKEND_DIR = CURRENT_DIR.parent

LR_ASD_DIR = BACKEND_DIR / "external" / "LR-ASD"

ASD_SCRIPT = LR_ASD_DIR / "Columbia_test.py"

DEMO_DIR = LR_ASD_DIR / "demo"


# -----------------------------------
# RUN ASD
# -----------------------------------
def run_asd(
    video_path: str,
    output_dir: str,
    python_executable: str = sys.executable,
    use_talkset_model: bool = False
):

    # -----------------------------------
    # VALIDATE INPUT
    # -----------------------------------
    if not os.path.exists(video_path):

        raise FileNotFoundError(
            f"\n❌ Video not found:\n{video_path}"
        )

    # -----------------------------------
    # CREATE DEMO DIR
    # -----------------------------------
    os.makedirs(
        DEMO_DIR,
        exist_ok=True
    )

    # -----------------------------------
    # VIDEO NAME
    # -----------------------------------
    video_name = Path(video_path).stem

    # -----------------------------------
    # COPY VIDEO TO DEMO
    # -----------------------------------
    demo_video_path = (
        DEMO_DIR /
        f"{video_name}.mp4"
    )

    print("\nCopying video...")

    shutil.copy2(
        video_path,
        demo_video_path
    )

    print(f"✅ Copied to: {demo_video_path}")

    # -----------------------------------
    # COMMAND
    # -----------------------------------
    command = [
        python_executable,

        str(ASD_SCRIPT),

        "--videoName",
        video_name,

        "--videoFolder",
        "demo"
    ]

    # optional TalkSet model
    if use_talkset_model:

        command.extend([
            "--pretrainModel",
            "weight/finetuning_TalkSet.model"
        ])

    # -----------------------------------
    # RUN PROCESS
    # -----------------------------------
    print("\nRunning LR-ASD...")
    print(" ".join(command))

    process = subprocess.run(
        command,
        cwd=str(LR_ASD_DIR),
        env=runtime_env(),
        text=True
    )

    # -----------------------------------
    # ERROR CHECK
    # -----------------------------------
    if process.returncode != 0:

        raise RuntimeError(
            "\n❌ LR-ASD failed"
        )

    print("\n✅ LR-ASD completed")

    # -----------------------------------
    # OUTPUT PATHS
    # -----------------------------------
    actual_output_dir = (
        DEMO_DIR /
        video_name /
        "pywork"
    )

    scores_path = (
        actual_output_dir /
        "scores.pckl"
    )

    tracks_path = (
        actual_output_dir /
        "tracks.pckl"
    )

    # -----------------------------------
    # VALIDATE OUTPUTS
    # -----------------------------------
    if not scores_path.exists():

        raise FileNotFoundError(
            f"\n❌ scores.pckl not found:\n{scores_path}"
        )

    if not tracks_path.exists():

        raise FileNotFoundError(
            f"\n❌ tracks.pckl not found:\n{tracks_path}"
        )

    print("\n✅ ASD outputs found")

    # -----------------------------------
    # FINAL OUTPUT DIR
    # -----------------------------------
    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # -----------------------------------
    # COPY OUTPUTS
    # -----------------------------------
    final_scores = os.path.join(
        output_dir,
        "scores.pckl"
    )

    final_tracks = os.path.join(
        output_dir,
        "tracks.pckl"
    )

    shutil.copy2(
        scores_path,
        final_scores
    )

    shutil.copy2(
        tracks_path,
        final_tracks
    )

    print("\n✅ Outputs copied")

    return {
        "scores_path": final_scores,
        "tracks_path": final_tracks,
        "output_dir": output_dir
    }


# -----------------------------------
# EXAMPLE USAGE
# -----------------------------------
if __name__ == "__main__":

    result = run_asd(
        video_path="clips/clip_0.mp4",
        output_dir="outputs/asd/test_video",
        use_talkset_model=False
    )

    print("\n========== RESULT ==========")
    print(result)
