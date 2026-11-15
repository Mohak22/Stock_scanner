# -*- coding: utf-8 -*-
"""
Created on Sun Nov 15 16:13:19 2026

@author: mohak
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("RESEARCH_AGENT_MODEL", "gemini-3.8-flash")

    if not api_key or api_key == "your_actual_gemini_api_key":
        raise RuntimeError("GEMINI_API_KEY is missing from .env")

    client = genai.Client(api_key=api_key)

    print("Testing Gemini generation...", flush=True)
    
    response = client.models.generate_content(
        model=model,
        contents="Reply with only OK.",
        config={
            "max_output_tokens": 20,
            "http_options": {"timeout": 60000}
        }
    )
    
    print("Response:", response.text)

    print("Gemini API connection successful.")
    print("Model:", model)
    # print("Response:", response.text)


if __name__ == "__main__":
    main()