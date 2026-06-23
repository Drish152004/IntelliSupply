import os
import re
import logging
import httpx
from config.env import load_env

logger = logging.getLogger(__name__)
load_env()

# Common offensive words list for fast local checks to save API quota and support offline validation
OFFENSIVE_KEYWORDS = {
    "shit", "idiot", "crap", "hate", "kill", "die"
}

# Regex to strip basic punctuation for keyword check normalization
PUNCTUATION_RE = re.compile(r"[^\w\s]")

def check_toxicity(text: str) -> bool:
    """
    Check if a given string contains toxic, hostile, or offensive language.
    First runs a local keyword check, and falls back to a Hugging Face toxicity classifier.
    
    Returns:
        bool: True if toxic/offensive content is detected, False otherwise.
    """
    if not text or not isinstance(text, str):
        return False

    cleaned_text = text.strip().lower()
    
    # 1. Local Blacklist Check
    # Normalize by removing basic punctuation to prevent bypasses like "idiot!"
    normalized_for_words = PUNCTUATION_RE.sub(" ", cleaned_text)
    words = set(normalized_for_words.split())
    
    # Check simple keywords
    for word in words:
        if word in OFFENSIVE_KEYWORDS:
            logger.warning("Toxicity detected via local keyword blacklist check.")
            return True
            
    # Check substrings/phrases (e.g. "hate you", "kill yourself")
    for phrase in OFFENSIVE_KEYWORDS:
        if len(phrase.split()) > 1 and phrase in cleaned_text:
            logger.warning("Toxicity detected via local phrase blacklist check.")
            return True

    # 2. Hugging Face Inference API Check
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        # Fail open if no token is configured
        logger.warning("HF_TOKEN not set; skipping Hugging Face toxicity check (fail-open).")
        return False

    model = os.getenv("HF_TOXICITY_MODEL", "textdetox/xlmr-large-toxicity-classifier")
    threshold_str = os.getenv("HF_TOXICITY_THRESHOLD", "0.5")
    try:
        threshold = float(threshold_str)
    except ValueError:
        threshold = 0.5

    url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": text}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
        
        # If model is loading, wait and retry once
        if response.status_code == 503:
            import time
            time.sleep(3)
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
                
        response.raise_for_status()
        data = response.json()

        # Handle different potential Hugging Face text classification return formats
        # Standard: [[{"label": "toxic", "score": 0.99}, {"label": "neutral", "score": 0.01}]]
        if isinstance(data, list) and data:
            predictions = data[0]
            if isinstance(predictions, list):
                for pred in predictions:
                    if isinstance(pred, dict):
                        label = str(pred.get("label", "")).lower()
                        score = float(pred.get("score", 0.0))
                        # Matches unitary/toxic-bert, textdetox/xlmr-large-toxicity-classifier labels
                        if label in ("toxic", "insult", "severe_toxic", "obscene", "threat", "identity_hate"):
                            if score >= threshold:
                                logger.warning("Toxicity detected via Hugging Face model %s: %s (score=%s)", model, label, score)
                                return True
    except Exception as exc:
        # Fail open, but log the warning/exception details
        logger.warning("Hugging Face toxicity validation failed (fail-open): %s", exc, exc_info=True)

    return False
