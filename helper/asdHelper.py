import numpy as np


# -----------------------------------
# MIN / MAX FRAMES
# -----------------------------------
def min_max_frames(tracks):

    all_frames = [
        np.array(track["track"]["frame"])
        for track in tracks
    ]

    min_frame = min(
        frames[0]
        for frames in all_frames
    )

    max_frame = max(
        frames[-1]
        for frames in all_frames
    )

    return min_frame, max_frame


# -----------------------------------
# MAX SCORE PER FRAME
# -----------------------------------
def max_score_per_frame(
    tracks,
    scores
):

    min_frame, max_frame = min_max_frames(
        tracks
    )

    score_frame = {}

    for frame in range(
        min_frame,
        max_frame + 1
    ):

        max_score = -100

        best_track_id = -1

        best_bbox = None

        # -----------------------------------
        # CHECK ALL TRACKS
        # -----------------------------------
        for track_id, track in enumerate(tracks):

            frames = track["track"]["frame"]

            track_scores = scores[track_id]

            idx = np.searchsorted(
                frames,
                frame
            )

            # frame not found
            if (
                idx >= len(frames)
                or
                frames[idx] != frame
            ):
                continue

            # first frame has no score
            if idx == 0:
                continue

            score_idx = idx - 1

            if score_idx >= len(track_scores):
                continue

            score = track_scores[
                score_idx
            ]

            if score > max_score:

                max_score = score

                best_track_id = track_id

                best_bbox = (
                    track["track"]["bbox"][idx]
                )

        # -----------------------------------
        # SAVE BEST TRACK
        # -----------------------------------
        if best_track_id != -1:

            score_frame[frame] = (
                frame,
                best_track_id,
                max_score,
                best_bbox
            )

    return score_frame


# -----------------------------------
# BUILD STABLE SPEAKER SEGMENTS
# -----------------------------------
def build_speaker_segments(
    frame_score,
    total_frames,
    MIN_FRAMES=30
):

    segments = []

    current_speaker = None

    candidate_speaker = None

    candidate_count = 0

    stable_speaker_per_frame = []

    # -----------------------------------
    # BUILD STABLE TIMELINE
    # -----------------------------------
    for frame in range(total_frames):

        if frame in frame_score:

            (
                _,
                detected_speaker,
                _,
                _
            ) = frame_score[frame]

        else:

            detected_speaker = None

        # -----------------------------------
        # INITIALIZE
        # -----------------------------------
        if current_speaker is None:

            current_speaker = (
                detected_speaker
            )

        # -----------------------------------
        # SAME SPEAKER
        # -----------------------------------
        elif detected_speaker == current_speaker:

            candidate_speaker = None

            candidate_count = 0

        # -----------------------------------
        # POSSIBLE SPEAKER SWITCH
        # -----------------------------------
        else:

            if candidate_speaker == detected_speaker:

                candidate_count += 1

            else:

                candidate_speaker = (
                    detected_speaker
                )

                candidate_count = 1

            # -----------------------------------
            # CONFIRM SWITCH
            # -----------------------------------
            if candidate_count >= MIN_FRAMES:

                current_speaker = (
                    candidate_speaker
                )

                candidate_speaker = None

                candidate_count = 0

        stable_speaker_per_frame.append(
            current_speaker
        )

    # -----------------------------------
    # FIX INITIAL NONE
    # -----------------------------------
    for i in range(
        len(stable_speaker_per_frame)
    ):

        if (
            stable_speaker_per_frame[i]
            is not None
        ):

            stable_speaker_per_frame[:i] = [
                stable_speaker_per_frame[i]
            ] * i

            break

    # -----------------------------------
    # CONVERT TO SEGMENTS
    # -----------------------------------
    raw_segments = []

    start = 0

    prev_speaker = (
        stable_speaker_per_frame[0]
    )

    for i in range(1, total_frames):

        if (
            stable_speaker_per_frame[i]
            !=
            prev_speaker
        ):

            raw_segments.append(
                (
                    start,
                    i - 1,
                    prev_speaker
                )
            )

            start = i

            prev_speaker = (
                stable_speaker_per_frame[i]
            )

    raw_segments.append(
        (
            start,
            total_frames - 1,
            prev_speaker
        )
    )

    # -----------------------------------
    # FILTER SHORT SEGMENTS
    # -----------------------------------
    for (
        start,
        end,
        speaker
    ) in raw_segments:

        length = end - start + 1

        if length >= MIN_FRAMES:

            segments.append(
                (
                    start,
                    end,
                    speaker
                )
            )

    return segments