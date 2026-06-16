"""
Multi-LLM client for benchmark evaluation.
Supports: Cohere Command-A, Google Gemini, Groq (Llama).
Each provider can be selected at runtime for A/B comparisons.
"""
import os
import time
import random

# ─────────────────────────────────────────────────────────────
# PROVIDER: COHERE
# ─────────────────────────────────────────────────────────────
def _call_cohere(prompt: str, model: str = "command-a-03-2025") -> str:
    import cohere
    api_key = os.getenv("COHERE_API_KEY", "")
    if not api_key:
        raise ValueError("COHERE_API_KEY not set")
    client = cohere.ClientV2(api_key)
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.message.content[0].text


# ─────────────────────────────────────────────────────────────
# PROVIDER: OPENROUTER (Gemini 2.5 Flash via OpenRouter)
# ─────────────────────────────────────────────────────────────
def _call_openrouter(prompt: str, model: str = "google/gemini-2.5-flash") -> str:
    import requests
    import json
    
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set. Add it to .streamlit/secrets.toml or set as environment variable.")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/google/geo-gee-llm-adv",
        "X-Title": "Geo-GEE-LLM Benchmark Evaluation"
    }
    
    # We restrict max_tokens to 2048 to avoid large credit reservation checks by OpenRouter
    data = {
        "model": model,
        "max_tokens": 2048,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(data)
    )
    
    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter API error: {response.status_code} {response.text}")
        
    res_json = response.json()
    time.sleep(2.0)  # Proactive sleep to respect OpenRouter's 10 RPM free limit
    return res_json["choices"][0]["message"]["content"]


# ─────────────────────────────────────────────────────────────
# PROVIDER: GROQ (Free - Llama models)
# ─────────────────────────────────────────────────────────────
def _call_groq(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4096,
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────
# UNIFIED DISPATCH
# ─────────────────────────────────────────────────────────────
PROVIDERS = {
    "cohere":      {"call": _call_cohere,      "model": "command-a-03-2025",        "label": "Cohere Command-A"},
    "openrouter":  {"call": _call_openrouter,  "model": "google/gemma-4-31b-it:free",   "label": "Gemma 4 31B (OpenRouter)"},
    "groq":        {"call": _call_groq,        "model": "llama-3.3-70b-versatile",  "label": "Llama 3.3 70B (Groq)"},
}


def call_llm_multi(prompt: str, provider: str = "cohere", max_retries: int = 6) -> str:
    """
    Call an LLM with retry logic. Provider selects which backend to use.
    
    Args:
        prompt: The prompt string.
        provider: One of 'cohere', 'gemini', 'groq'.
        max_retries: Number of retries on transient errors.
    
    Returns:
        The LLM response text.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(PROVIDERS.keys())}")
    
    config = PROVIDERS[provider]
    call_fn = config["call"]
    model = config["model"]
    
    for attempt in range(max_retries + 1):
        try:
            return call_fn(prompt, model)
        except Exception as e:
            error_msg = str(e).lower()
            is_transient = any(x in error_msg for x in ["429", "500", "502", "503", "504", "timeout", "connection", "rate"])
            
            if attempt >= max_retries or not is_transient:
                raise
            
            if "429" in error_msg or "rate" in error_msg:
                delay = 25.0 + random.uniform(0, 5.0)
                print(f"  [Rate Limit Retry {attempt+1}/{max_retries}] {provider} hit 429. Waiting {delay:.1f}s to reset window...")
            else:
                delay = (2 ** attempt) + random.uniform(0, 0.5)
                print(f"  [Retry {attempt+1}/{max_retries}] {provider} failed: {str(e)[:100]}. Waiting {delay:.1f}s...")
            time.sleep(delay)
