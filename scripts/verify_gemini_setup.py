#!/usr/bin/env python3
"""Verify Gemini API key and model availability."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def mask_key(key: str) -> str:
    if not key:
        return "MISSING"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def try_generate(model: str, api_key: str) -> dict:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    client = genai.GenerativeModel(model)
    try:
        response = client.generate_content(
            "Reply with exactly: OK",
            generation_config={"max_output_tokens": 16, "temperature": 0},
        )
        text = (response.text or "").strip()
        return {"ok": True, "model": model, "response_preview": text[:80]}
    except Exception as e:
        err = str(e)
        return {
            "ok": False,
            "model": model,
            "error_type": type(e).__name__,
            "error_preview": err[:500],
        }


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("GOOGLE_API_KEY", "")
    llm_provider = os.getenv("LLM_PROVIDER", "gemini")
    llm_model = os.getenv("LLM_MODEL", "financial")

    if not api_key:
        print("GOOGLE_API_KEY is missing. Set it in .env (copy from .env.example).")
        return 1

    from trading_agent.llm.gemini_client import GeminiClient

    configured = GeminiClient.AVAILABLE_MODELS.get(llm_model, llm_model)
    candidates = [configured, "gemini-3.1-flash-lite-preview", "gemini-3.5-flash"]
    seen = set()
    unique_candidates = []
    for model in candidates:
        if model not in seen:
            seen.add(model)
            unique_candidates.append(model)

    results = [try_generate(model, api_key) for model in unique_candidates]
    working = [r for r in results if r.get("ok")]

    print("\nGemini API verification")
    print("=" * 50)
    print(f"GOOGLE_API_KEY: {mask_key(api_key)} (length {len(api_key)})")
    print(f"LLM_PROVIDER={llm_provider}, LLM_MODEL={llm_model} -> {configured}")

    print("\nModel probes:")
    for r in results:
        status = "OK" if r.get("ok") else "FAILED"
        print(f"  {r['model']} -> {status}")
        if r.get("ok"):
            print(f"    response: {r.get('response_preview')}")
        elif r.get("error_preview"):
            print(f"    {r['error_preview'][:200]}")

    if working:
        print(f"\nAt least one model works. Default in gemini_client: {GeminiClient.DEFAULT_MODEL}")
    else:
        print(
            "\nNo model succeeded. Enable billing or create a key at "
            "https://aistudio.google.com/apikey"
        )

    return 0 if working else 1


if __name__ == "__main__":
    raise SystemExit(main())
