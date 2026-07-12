"""
User profile tool.

Provides access to user profile information.
"""

import json
import random
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"


def get_user() -> dict[str, Any]:
    """
    Retrieve the current user's profile information.

    Returns:
        Dictionary containing user profile data:
        - user_id: str
        - name: str
        - age: int
        - language_preference: str (e.g., "en", "es")
        - accessibility: dict with preferences like:
            - large_text: bool
            - screen_reader: bool
            - high_contrast: bool

    Raises:
        TimeoutError: Randomly, to simulate network issues
    """
    # Simulate occasional network timeout
    if random.random() < 0.05:
        raise TimeoutError("Profile service temporarily unavailable")

    with open(DATA_DIR / "users.json", "r") as f:
        users = json.load(f)

    # Return the first (and only) user for this assignment
    user = users[0]

    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "age": user["age"],
        "language_preference": user.get("preferences", {}).get("language", "en"),
        "accessibility": {
            "large_text": user.get("preferences", {}).get("large_text", False),
            "screen_reader": user.get("preferences", {}).get("screen_reader", False),
            "high_contrast": user.get("preferences", {}).get("high_contrast", False),
        }
    }
