import os
import cv2
import pickle
import subprocess
import numpy as np

from pathlib import Path

from asdHelper import (
    max_score_per_frame,
    build_speaker_segments
)


# -----------------------------------
# GET BBOX
# -----------------------------------
def get_bbox_for_frame(track, frame):

    frames = track["track"]["frame"]
    bboxes = track["track"]["bbox"]

    idx = np.searchsorted(frames, frame)

    if idx < len(frames) and frames[idx] == frame:
        return bboxes[idx]

    return None


# -----------------------------------
# GET CENTER
# -----------------------------------
def get_center_from_bbox(bbox):

    x1, y1, x2, y2 = map(int, bbox)

    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2

    return cx, cy


# -----------------------------------
# CROP SINGLE VIDEO
# -----------------------------------
def crop_video(
    video_path,
    segments,
    tracks,
    output_path
):

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():

        print(f"❌ Failed to open: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    ret, frame = cap.read()

    if not ret:

        print("❌ Failed to read first frame")
        return

    h, w, _ = frame.shape

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    OUT_W = int(h * 9 / 16)
    OUT_H = h

    frame_idx = 0
    segment_idx = 0

    # -----------------------------------
    # SMOOTHING
    # -----------------------------------
    smooth_cx = None
    smooth_cy = None

    alpha = 0.08

    last_valid_cx = None
    last_valid_cy = None

    last_valid_bbox = None

    none_count = 0
    NONE_THRESHOLD = 40

    # -----------------------------------
    # FFMPEG PIPE
    # -----------------------------------
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",

        "-f", "rawvideo",
        "-vcodec", "rawvideo",

        "-pix_fmt", "bgr24",

        "-s", f"{OUT_W}x{OUT_H}",
        "-r", str(int(fps)),

        "-i", "-",

        "-i", video_path,

        "-map", "0:v:0",
        "-map", "1:a:0",

        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",

        "-c:a", "aac",

        "-shortest",

        output_path
    ]

    process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE
    )

    # -----------------------------------
    # MAIN LOOP
    # -----------------------------------
    while True:

        ret, frame = cap.read()

        if not ret:
            break

        # -----------------------------------
        # CURRENT SEGMENT
        # -----------------------------------
        start, end, speaker = segments[segment_idx]

        if (
            frame_idx > end and
            segment_idx < len(segments) - 1
        ):

            segment_idx += 1
            start, end, speaker = segments[segment_idx]

        # -----------------------------------
        # GET BBOX
        # -----------------------------------
        best_bbox = None

        if speaker is not None:

            track = tracks[speaker]

            best_bbox = get_bbox_for_frame(
                track,
                frame_idx
            )

        # -----------------------------------
        # HANDLE MISSING BBOX
        # -----------------------------------
        if best_bbox is not None:

            last_valid_bbox = best_bbox
            none_count = 0

        else:

            none_count += 1

            if none_count < NONE_THRESHOLD:
                best_bbox = last_valid_bbox

        # -----------------------------------
        # GET CENTER
        # -----------------------------------
        if best_bbox is not None:

            cx, cy = get_center_from_bbox(
                best_bbox
            )

            last_valid_cx = cx
            last_valid_cy = cy

        else:

            cx = last_valid_cx
            cy = last_valid_cy

        # -----------------------------------
        # DEFAULT CENTER
        # -----------------------------------
        if cx is None:

            cx = w // 2
            cy = h // 2

        # -----------------------------------
        # SMOOTH CENTER
        # -----------------------------------
        if smooth_cx is None:

            smooth_cx = cx
            smooth_cy = cy

        else:

            smooth_cx = int(
                smooth_cx +
                (cx - smooth_cx) * alpha
            )

            smooth_cy = int(
                smooth_cy +
                (cy - smooth_cy) * alpha
            )

        # -----------------------------------
        # CROP WINDOW
        # -----------------------------------
        crop_w = OUT_W

        x1_crop = smooth_cx - crop_w // 2
        x2_crop = smooth_cx + crop_w // 2

        target_y = int(h * 0.35)

        offset = smooth_cy - target_y

        y1_crop = offset
        y2_crop = offset + h

        # -----------------------------------
        # CLAMP X
        # -----------------------------------
        if x1_crop < 0:

            x2_crop -= x1_crop
            x1_crop = 0

        if x2_crop > w:

            shift = x2_crop - w

            x1_crop -= shift
            x2_crop = w

        # -----------------------------------
        # CLAMP Y
        # -----------------------------------
        if y1_crop < 0:

            y2_crop -= y1_crop
            y1_crop = 0

        if y2_crop > h:

            shift = y2_crop - h

            y1_crop -= shift
            y2_crop = h

        # -----------------------------------
        # CROP
        # -----------------------------------
        cropped = frame[
            y1_crop:y2_crop,
            x1_crop:x2_crop
        ]

        cropped = cv2.resize(
            cropped,
            (OUT_W, OUT_H)
        )

        # -----------------------------------
        # WRITE FRAME
        # -----------------------------------
        process.stdin.write(
            cropped.tobytes()
        )

        frame_idx += 1

    # -----------------------------------
    # CLEANUP
    # -----------------------------------
    cap.release()

    process.stdin.close()
    process.wait()

    print(f"✅ Saved: {output_path}")


# -----------------------------------
# PROCESS SINGLE CLIP
# -----------------------------------
def process_clip(
    clip_video_path,
    asd_output_dir,
    output_video_path
):

    # -----------------------------------
    # LOAD ASD OUTPUTS
    # -----------------------------------
    scores_path = os.path.join(
        asd_output_dir,
        "scores.pckl"
    )

    tracks_path = os.path.join(
        asd_output_dir,
        "tracks.pckl"
    )

    with open(scores_path, "rb") as f:
        scores = pickle.load(f)

    with open(tracks_path, "rb") as f:
        tracks = pickle.load(f)

    # -----------------------------------
    # FRAME SCORES
    # -----------------------------------
    frame_score = max_score_per_frame(
        tracks,
        scores
    )

    # -----------------------------------
    # TOTAL FRAMES
    # -----------------------------------
    cap = cv2.VideoCapture(
        clip_video_path
    )

    total_frames = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    cap.release()

    # -----------------------------------
    # BUILD SEGMENTS
    # -----------------------------------
    segments = build_speaker_segments(
        frame_score,
        total_frames,
        MIN_FRAMES=30
    )

    # -----------------------------------
    # CROP VIDEO
    # -----------------------------------
    crop_video(
        clip_video_path,
        segments,
        tracks,
        output_video_path
    )


# -----------------------------------
# PROCESS ALL CLIPS
# -----------------------------------
def process_all_clips(
    clips_dir="clips",
    asd_outputs_dir="outputs/asd",
    final_output_dir="outputs/final"
):

    os.makedirs(
        final_output_dir,
        exist_ok=True
    )

    clip_files = sorted([
        file
        for file in os.listdir(clips_dir)
        if file.endswith(".mp4")
    ])

    for clip_file in clip_files:

        clip_name = Path(
            clip_file
        ).stem

        print("\n")
        print("=" * 50)
        print(f"🎬 Processing {clip_name}")
        print("=" * 50)

        clip_path = os.path.join(
            clips_dir,
            clip_file
        )

        asd_dir = os.path.join(
            asd_outputs_dir,
            clip_name
        )

        output_video_path = os.path.join(
            final_output_dir,
            f"{clip_name}.mp4"
        )

        try:

            process_clip(
                clip_video_path=clip_path,
                asd_output_dir=asd_dir,
                output_video_path=output_video_path
            )

            print(f"✅ Finished {clip_name}")

        except Exception as e:

            print(f"❌ Failed {clip_name}")
            print(str(e))


# -----------------------------------
# EXAMPLE USAGE
# -----------------------------------
if __name__ == "__main__":

    process_all_clips(
        clips_dir="clips",
        asd_outputs_dir="outputs/asd",
        final_output_dir="outputs/final"
    )