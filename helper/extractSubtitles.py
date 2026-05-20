import whisperx
import gc
import torch
import json
import os

from dotenv import load_dotenv
from whisperx.diarize import DiarizationPipeline

# -----------------------------------
# LOAD ENV
# -----------------------------------
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")


# -----------------------------------
# MAIN FUNCTION
# -----------------------------------
def transcribe_with_diarization(
    audio_file: str,
    output_file: str = "output.json",
    model_size: str = "small",
    device: str = "cpu",
    batch_size: int = 2,
    compute_type: str = "int8_float16"
):

    # -----------------------------------
    # LOAD AUDIO
    # -----------------------------------
    audio = whisperx.load_audio(audio_file)

    # -----------------------------------
    # STEP 1: TRANSCRIBE
    # -----------------------------------
    print("\nLoading Whisper model...")

    model = whisperx.load_model(
        model_size,
        device,
        compute_type=compute_type
    )

    print("Transcribing audio...")

    result = model.transcribe(
        audio,
        batch_size=batch_size
    )

    print("\nBefore diarization:")
    print(result["segments"])

    # -----------------------------------
    # FREE WHISPER MODEL
    # -----------------------------------
    del model

    gc.collect()
    torch.cuda.empty_cache()

    # -----------------------------------
    # STEP 2: DIARIZATION
    # -----------------------------------
    print("\nLoading diarization model...")

    diarize_model = DiarizationPipeline(
        token=HF_TOKEN,
        device=device
    )

    print("Running diarization...")

    diarize_segments = diarize_model(audio)

    # -----------------------------------
    # ASSIGN SPEAKERS
    # -----------------------------------
    result = whisperx.assign_word_speakers(
        diarize_segments,
        result
    )

    print("\nAfter diarization:")
    print(result["segments"])

    # -----------------------------------
    # SIMPLIFIED OUTPUT
    # -----------------------------------
    simplified_output = []

    for segment in result["segments"]:

        simplified_segment = {
            "text": segment.get("text", ""),
            "start": segment.get("start"),
            "end": segment.get("end"),
            "avg_logprob": segment.get(
                "avg_logprob",
                None
            ),
            "speaker": segment.get(
                "speaker",
                "UNKNOWN"
            )
        }

        simplified_output.append(
            simplified_segment
        )

    # -----------------------------------
    # SAVE JSON
    # -----------------------------------
    with open(output_file, "w") as f:

        json.dump(
            simplified_output,
            f,
            indent=4
        )

    print(f"\nSaved output to {output_file}")

    # -----------------------------------
    # CLEANUP
    # -----------------------------------
    del diarize_model

    gc.collect()
    torch.cuda.empty_cache()

    return simplified_output


# -----------------------------------
# EXAMPLE USAGE
# -----------------------------------
if __name__ == "__main__":

    result = transcribe_with_diarization(
        audio_file="downloads/video.mp3",
        output_file="output4.json",
        model_size="small",
        device="cuda",
        batch_size=2,
        compute_type="float16"
    )

    print("\nDone!")