import os
import json
import base64
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai  # <-- Import Google
from mimetypes import guess_type

# Assuming 'combine_analysis_to_json' is in a file named 'w.py'
from w import combine_analysis_to_json 

# ---- Configuration ----
load_dotenv()
logger = logging.getLogger("wheel-sync")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Use a text-only Gemini model ---
MODEL = "gemini-2.5-flash"
DB_PATH = r'..\Documents\Elevatoin_Points_Section_B_8300322035806414704.xlsx'
IMAGE_PATH = r'C:\Users\gurpr\Pictures\Screenshots\Screenshot 2025-11-08 130917.png'

# --- Use Google API Key ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is required in your .env")

def load_env_prompt() -> str:
    p = os.getenv("AI_PROMPT")
    if not p:
        raise RuntimeError("AI_PROMPT env var is required and was not found.")
    return p

def encode_image_base64(image_path: str) -> str:
    """Encodes the image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def build_user_context_json(db_path: str, image_path: str) -> str:
    """
    Creates the user-facing JSON context string.
    """
    # Get the analysis data
    combined_json_str = combine_analysis_to_json(db_path, image_path, pretty=False)
    try:
        combined_json = json.loads(combined_json_str) if isinstance(combined_json_str, str) else combined_json_str
    except Exception:
        combined_json = combined_json_str

    # Build the payload structure
    user_payload = {
        "context_provenance": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "db_path": db_path,
            "image_path": image_path
        },
        "analysis": combined_json
    }
    user_text = json.dumps(user_payload, ensure_ascii=False)
    
    # Log info
    preview_len = min(2048, len(user_text))
    logger.info("USER CONTEXT JSON length: %d chars", len(user_text))
    logger.info("USER CONTEXT JSON preview (first %d chars): %s", preview_len, user_text[:preview_len].replace("\n", " "))
    
    return user_text

def extract_text_from_response(resp) -> str:
    """Extracts the text content from a Gemini API response."""
    try:
        # The simple path
        return resp.text
    except Exception:
        logger.warning("Could not access .text, trying to parse candidates.")
        try:
            # The more complex path
            for part in resp.candidates[0].content.parts:
                if part.text:
                    return part.text
        except Exception:
            pass # Fall through to stringify
            
    # last resort: stringify entire response
    logger.error("Could not parse response text directly.")
    try:
        return json.dumps(resp, default=str)
    except Exception:
        return str(resp)

# aa.py (FIXED validate_and_parse_json function)

def validate_and_parse_json(text: str) -> dict:
    """
    Ensure the model returned a single JSON object. Raises ValueError on parse issues.
    """
    # Trim whitespace
    txt = text.strip()

    # --- FIX: New, more aggressive code fence and stray text removal ---
    # Try to find the start of the actual JSON object '{'
    first = txt.find("{")
    # Try to find the end of the actual JSON object '}'
    last = txt.rfind("}")

    if first == -1 or last == -1 or last <= first:
        # If we can't find a JSON block, raise an error
        raise ValueError("Model output does not contain a valid JSON object.")
        
    # Slice the text to get ONLY the content from the first '{' to the last '}'
    txt = txt[first:last+1]
    
    # --- END FIX ---
    
    parsed = json.loads(txt)
    if not isinstance(parsed, dict):
        raise ValueError("Parsed JSON is not an object.")
    
    # --- Key validation remains the same and is correct ---
    required_keys = {"Tread_Spacing", "Tire_Thickness", "Tire_OD", "Tread_Thickness", "reasoning"}
    missing = required_keys - set(parsed.keys())
    if missing:
        raise ValueError(f"JSON missing required keys: {missing}")
    
    # --- Constraint check remains the same ---
    spacing = parsed.get("Tread_Spacing")
    if spacing is not None and not isinstance(spacing, (int, float)):
         raise ValueError("Tread_Spacing must be a number.")
    if spacing is not None and 360 % spacing != 0:
         pass 
         
    return parsed

def main():
    try:
        # 1. Configure the Google client
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # 2. Load the system prompt
        ai_prompt = load_env_prompt()
        logger.info("SYSTEM PROMPT (AI_PROMPT): %s", ai_prompt)
        
        # 3. Set up the GenerativeModel with the system prompt
        model = genai.GenerativeModel(
            MODEL,
            system_instruction=ai_prompt
        )

        # 4. Prepare the user content (JSON text ONLY)
        user_context_text = build_user_context_json(DB_PATH, IMAGE_PATH)
        
        # --- IMAGE CODE REMOVED ---
        # All the code for loading the image,
        # guessing mime_type, and creating image_part
        # has been deleted as requested.
        
        # 5. Send synchronous request to model
        logger.info("Sending synchronous request to model (%s)...", MODEL)
        
        # --- UPDATED CALL ---
        # We now send *only* the text context, not a list.
        resp = model.generate_content(user_context_text)
        
        logger.info("Response received; extracting text...")
        text = extract_text_from_response(resp)

        logger.info("Raw model output (trimmed preview): %s", text[:200].replace("\n", " "))
        try:
            parsed = validate_and_parse_json(text)
            # Print pretty JSON to stdout for pipeline consumption
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error("Failed to validate/parse model JSON: %s", str(e))
            logger.debug("Full model output:\n%s", text)
            raise

    except Exception as exc:
        logger.error("Pipeline failed: %s", str(exc))
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    main()