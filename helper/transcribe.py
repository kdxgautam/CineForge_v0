import gc
import torch
import json
import os

from .whisperx_compat import load_whisperx



def generate_word_level_transcript(
    video_path: str,
    output_json: str,
    model_size: str = "small",
    device: str = "cuda",
    batch_size: int = 1,
    compute_type: str = "int8"
):
    whisperx = load_whisperx()

    # -----------------------------------
    # LOAD MODEL
    # -----------------------------------
    model = whisperx.load_model(
        model_size,
        device,
        compute_type=compute_type
    )

    # -----------------------------------
    # LOAD AUDIO
    # -----------------------------------
    audio = whisperx.load_audio(
        video_path
    )

    # -----------------------------------
    # TRANSCRIBE
    # -----------------------------------
    result = model.transcribe(
        audio,
        batch_size=batch_size
    )

    # -----------------------------------
    # FREE MEMORY
    # -----------------------------------
    del model

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # -----------------------------------
    # ALIGNMENT
    # -----------------------------------
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"],
        device=device
    )

    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False
    )

    # -----------------------------------
    # FREE MEMORY
    # -----------------------------------
    del model_a

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # -----------------------------------
    # SAVE JSON
    # -----------------------------------
    output_dir = os.path.dirname(output_json)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_json, "w") as f:

        json.dump(
            result,
            f,
            indent=4
        )

    print(
        f"\n✅ Saved transcript:\n{output_json}"
    )

    return result
