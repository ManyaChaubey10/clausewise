"""Application settings and limits."""
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# JSON structured output for the Gemini Developer API is enabled on v1beta.
GEMINI_API_VERSION = "v1beta"
MAX_UPLOAD_MB = 20
MAX_DOCUMENT_CHARS = 250_000
CHUNK_CHARS = 20_000
CHUNK_OVERLAP = 800
RISK_CATEGORIES = [
    "Automatic subscription renewals", "Data collection and sharing",
    "Third-party access to personal information", "Cancellation and refund restrictions",
    "Unilateral changes to terms", "Arbitration and dispute resolution",
    "Liability limitations", "Account termination",
]
