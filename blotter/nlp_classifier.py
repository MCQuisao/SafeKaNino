import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "priority_keywords.json")

with open(JSON_PATH, "r", encoding="utf-8") as f:
    RULES = json.load(f)

def detect_priority(text):
    text = str(text).lower()

    for keyword in RULES["critical"]:
        if keyword in text:
            return "Critical"

    for keyword in RULES["high"]:
        if keyword in text:
            return "High"

    for keyword in RULES["medium"]:
        if keyword in text:
            return "Medium"

    return "Low"