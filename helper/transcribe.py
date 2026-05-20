import whisperx
import gc
import torch
import json
import os



def generate_word_level_transcript(
    video_path: str,
    output_json: str,
    model_size: str = "small",
    device: str = "cuda"
):

    # -----------------------------------
    # CONFIG
    # -----------------------------------
    batch_size = 1
    compute_type = "int8"

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
    torch.cuda.empty_cache()

    # -----------------------------------
    # SAVE JSON
    # -----------------------------------
    os.makedirs(
    os.path.dirname(output_json),
    exist_ok=True
)
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

generate_word_level_transcript(
    video_path="clips/clip_0.mp4",
    output_json="outputs/transcripts/clip_0.json",
    model_size="small",
    device="cuda")