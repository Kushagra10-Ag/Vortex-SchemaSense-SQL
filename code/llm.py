"""The ONLY place that talks to a model. Change provider/model with environment variables."""
import os
import time

_clients = {}  # one client per provider, created once and kept alive


def _client(provider):
    if provider not in _clients:
        if provider == "anthropic":
            import anthropic
            _clients[provider] = anthropic.Anthropic()
        elif provider == "openai":
            from openai import OpenAI
            _clients[provider] = OpenAI()
        elif provider == "gemini":
            from google import genai
            key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")
            if not key:
                raise RuntimeError("No API key found. Set GEMINI_API_KEY.")
            _clients[provider] = genai.Client(api_key=key)
        else:
            raise RuntimeError(f"Unknown LLM_PROVIDER: {provider}")
    return _clients[provider]


def call_llm(system: str, user: str, temperature=None, max_tokens: int = 800) -> str:
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    model = os.environ.get("MODEL_NAME", "")
    if not provider or not model:
        raise RuntimeError("Set LLM_PROVIDER (anthropic|openai|gemini) and MODEL_NAME. See .env.example")
    time.sleep(float(os.environ.get("CALL_DELAY", "0")))  # slows requests to respect free-tier limits
    last = None
    for attempt in range(6):
        try:
            return _call(provider, model, system, user, temperature, max_tokens)
        except Exception as e:
            last = e
            msg = str(e).lower()
            if temperature is not None and "temperature" in msg:
                temperature = None  # model rejects temperature: retry without it
            busy = any(k in msg for k in ("429", "503", "resource_exhausted", "unavailable", "overloaded", "rate"))
            time.sleep(min(10 * 2 ** attempt, 60) if busy else 2)  # 10s, 20s, 40s, 60s... for busy/limit errors
    raise last


def _call(provider, model, system, user, temperature, max_tokens):
    client = _client(provider)
    if provider == "anthropic":
        kw = {} if temperature is None else {"temperature": temperature}
        r = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                                   messages=[{"role": "user", "content": user}], **kw)
        return r.content[0].text
    if provider == "openai":
        kw = {} if temperature is None else {"temperature": temperature}
        r = client.chat.completions.create(model=model, messages=[{"role": "system", "content": system},
                                           {"role": "user", "content": user}], **kw)
        return r.choices[0].message.content
    if provider == "gemini":
        cfg = {"system_instruction": system}
        if temperature is not None:
            cfg["temperature"] = temperature
        r = client.models.generate_content(model=model, contents=user, config=cfg)
        return r.text