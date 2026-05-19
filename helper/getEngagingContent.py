from google import genai
from google.genai import types

from dotenv import load_dotenv

from subtitleParser import srt_to_json

import os
import json
import re

# -----------------------------------
# LOAD ENV
# -----------------------------------
load_dotenv()

# -----------------------------------
# GEMINI CLIENT
# -----------------------------------
client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)

# -----------------------------------
# SYSTEM INSTRUCTION
# -----------------------------------
SYSTEM_INSTRUCTION = """
You are an expert content editor specializing in identifying highly engaging short-form video clips from long-form transcripts.

Your task is to analyze a transcript consisting of multiple segments. Each segment contains:

* text (spoken content)
* start timestamp (in seconds)
* end timestamp (in seconds)

Your goal is to extract the most engaging clips suitable for platforms like YouTube Shorts, Instagram Reels, or TikTok.

Follow these rules strictly:

1. Engagement Criteria:
   Select segments that include:

* strong hooks (attention-grabbing openings)
* emotional intensity (excitement, surprise, controversy, humor)
* clear and complete ideas (not cut mid-thought)
* opinions, debates, or bold statements
* storytelling moments or valuable insights

Avoid:

* filler content
* greetings or introductions (unless highly engaging)
* incomplete or fragmented sentences

2. Clip Construction:

* Combine multiple consecutive segments if needed to form a meaningful clip
* Each clip MUST be at least 90 seconds long
* Prefer clips between 90–180 seconds
* Ensure the clip has a natural start and end

3. Output Requirements:
   Return ONLY a JSON array with the following structure:

[
{
"start": <start_timestamp>,
"end": <end_timestamp>,
"reason": "<why this clip is engaging>",
"content": "<the actual text content of the clip>"
}
]

4. Constraints:

* Do NOT hallucinate timestamps
* Use ONLY timestamps provided in the input
* Ensure start < end
* Do NOT include any explanation outside JSON
* Select only the top 3–5 best clips

5. Thinking Strategy:

* First identify engaging segments
* Then group adjacent segments into longer clips
* Then validate duration >= 90 seconds
* Then finalize the best clips

Your output must be clean, valid JSON.
"""


# -----------------------------------
# MAIN FUNCTION
# -----------------------------------
def generate_highlights(
    transcript_file: str,
    output_file: str = "highlights.json",
    model_name: str = "gemini-2.5-flash",
    max_segments: int = 50
):
    """
    Generate engaging video highlights
    from transcript JSON/SRT.
    """

    # -----------------------------------
    # LOAD TRANSCRIPT
    # -----------------------------------
    print("\nLoading transcript...")

    text = srt_to_json(transcript_file)

    # limit context
    contents = json.dumps(
        text[:max_segments],
        indent=2
    )

    # -----------------------------------
    # GEMINI REQUEST
    # -----------------------------------
    print("\nGenerating highlights...")

    response = client.models.generate_content(
        model=model_name,

        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        ),

        contents=contents
    )

    output = response.text

    # -----------------------------------
    # EXTRACT JSON SAFELY
    # -----------------------------------
    match = re.search(
        r"\[.*\]",
        output,
        re.DOTALL
    )

    if not match:

        print("\n❌ Failed to parse JSON")
        print(output)

        return None

    # -----------------------------------
    # LOAD JSON
    # -----------------------------------
    highlights = json.loads(
        match.group()
    )

    # -----------------------------------
    # SAVE OUTPUT
    # -----------------------------------
    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            highlights,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"\n Saved highlights to {output_file}"
    )

    return highlights


# -----------------------------------
# EXAMPLE USAGE
# -----------------------------------
if __name__ == "__main__":

    highlights = generate_highlights(
        transcript_file="output4.json",
        output_file="highlights.json",
        model_name="gemini-2.5-flash",
        max_segments=50
    )

    print("\nDone!")