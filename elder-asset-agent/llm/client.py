import os
import json
from typing import Any

from google import genai
from dotenv import load_dotenv


class LLMClient:
    def __init__(self, model: str = "gemini-3.1-flash-lite"):
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Get your key at https://aistudio.google.com/apikey"
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, messages: list[dict], temperature: float = 0.3) -> str:
        """
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
            Default 0.3 for factual/grounded responses.
        """
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        # Build config
        config = {"temperature": temperature}
        if system_instruction:
            config["system_instruction"] = system_instruction

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        return response.text or ""

    def generate_json(self, messages: list[dict], temperature: float = 0.1) -> dict[str, Any]:
        response_text = self.generate(messages, temperature=temperature)
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)
