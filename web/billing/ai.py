"""Server-side AI calls. The browser sends a prompt; the key stays here.

Token savings, in order of size:
  1. The app's built-in matcher handles most lines, so most entries never reach here.
  2. The app sends only the few products that share words with the text, one compact line each.
  3. Replies are capped (max_tokens) and use short JSON keys.
  4. An identical prompt to the same model is answered from the cache: 0 tokens.
  5. An optional monthly token limit stops runaway spend.
"""
import hashlib
import json
import urllib.error
import urllib.request
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import AICache, AICall, AIConfig

PRESETS = {
    "none": {"label": "Off: built-in matching only", "base": "", "model": ""},
    "groq": {"label": "Groq (free tier)", "base": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile", "keys": "console.groq.com/keys"},
    "gemini": {"label": "Google Gemini (free tier)", "base": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.5-flash", "keys": "aistudio.google.com/apikey"},
    "openrouter": {"label": "OpenRouter (has free models)", "base": "https://openrouter.ai/api/v1", "model": "meta-llama/llama-3.3-70b-instruct:free", "keys": "openrouter.ai/keys"},
    "deepseek": {"label": "DeepSeek", "base": "https://api.deepseek.com/v1", "model": "deepseek-chat", "keys": "platform.deepseek.com"},
    "openai": {"label": "OpenAI", "base": "https://api.openai.com/v1", "model": "gpt-4.1-mini", "keys": "platform.openai.com/api-keys"},
    "anthropic": {"label": "Anthropic (Claude)", "base": "https://api.anthropic.com/v1", "model": "claude-haiku-5-5", "keys": "console.anthropic.com"},
    "custom": {"label": "Other (OpenAI-compatible)", "base": "", "model": ""},
}
MAX_PROMPT_CHARS = 20000
MAX_OUTPUT_TOKENS = 2000
CACHE_DAYS = 30


class AIError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def resolved(cfg=None):
    cfg = cfg or AIConfig.get()
    p = PRESETS.get(cfg.provider, {})
    return {
        "provider": cfg.provider,
        "base": (cfg.base or p.get("base", "")).rstrip("/"),
        "model": cfg.model or p.get("model", ""),
        "key": cfg.key,
    }


def is_ready(cfg=None):
    c = resolved(cfg)
    return c["provider"] != "none" and bool(c["key"] and c["base"] and c["model"])


def month_usage():
    start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    qs = AICall.objects.filter(created__gte=start)
    agg = qs.filter(cached=False).aggregate(i=Sum("input_tokens"), o=Sum("output_tokens"))
    return {
        "calls": qs.filter(cached=False, ok=True).count(),
        "cached": qs.filter(cached=True).count(),
        "failed": qs.filter(ok=False).count(),
        "input": agg["i"] or 0,
        "output": agg["o"] or 0,
    }


def _post(url, headers, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:300]}
    except (urllib.error.URLError, TimeoutError) as e:
        raise AIError("network", f"Couldn't reach the AI service ({getattr(e, 'reason', e)}).", 502)


def _call(c, prompt, max_tokens):
    """Returns (text, input_tokens, output_tokens)."""
    if c["provider"] == "anthropic":
        status, data = _post(c["base"] + "/messages",
                             {"x-api-key": c["key"], "anthropic-version": "2023-06-01"},
                             {"model": c["model"], "max_tokens": max_tokens, "temperature": 0,
                              "messages": [{"role": "user", "content": prompt}]})
        if status == 200:
            text = "".join(b.get("text", "") for b in data.get("content", []))
            u = data.get("usage", {})
            return text, u.get("input_tokens", 0), u.get("output_tokens", 0)
    else:
        body = {"model": c["model"], "temperature": 0, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]}
        status, data = _post(c["base"] + "/chat/completions", {"Authorization": "Bearer " + c["key"]}, body)
        if status == 400 and "max_completion_tokens" in json.dumps(data):
            body.pop("max_tokens")
            body["max_completion_tokens"] = max_tokens
            status, data = _post(c["base"] + "/chat/completions", {"Authorization": "Bearer " + c["key"]}, body)
        if status == 200:
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            u = data.get("usage", {})
            return text, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
    detail = json.dumps(data)[:200]
    if status in (401, 403):
        raise AIError("bad_key", "The AI key was rejected. Check it in Settings.", 400)
    if status == 429:
        raise AIError("rate_limited", "AI limit reached. Wait a minute and try again.", 429)
    if status in (400, 404):
        msg = "The AI model name wasn't accepted. Check it in Settings." if "model" in detail.lower() else "The AI request was refused: " + detail
        raise AIError("bad_model", msg, 400)
    raise AIError("failed", f"AI request failed ({status}).", 502)


def complete(prompt, max_tokens=600, use_cache=True):
    cfg = AIConfig.get()
    if not is_ready(cfg):
        raise AIError("not_configured", "No AI key set. Add one in Settings.", 400)
    prompt = str(prompt or "")
    if not prompt.strip():
        raise AIError("empty", "Nothing to send.", 400)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise AIError("too_long", "That text is too long for one request.", 400)
    max_tokens = max(16, min(int(max_tokens or 600), MAX_OUTPUT_TOKENS))
    c = resolved(cfg)

    key = hashlib.sha256(f'{c["provider"]}|{c["model"]}|{max_tokens}|{prompt}'.encode()).hexdigest()
    if use_cache:
        hit = AICache.objects.filter(key=key, created__gte=timezone.now() - timedelta(days=CACHE_DAYS)).first()
        if hit:
            AICall.objects.create(provider=c["provider"], model=c["model"], cached=True)
            return {"text": hit.text, "cached": True, "input": 0, "output": 0}

    if cfg.monthly_token_limit:
        u = month_usage()
        if u["input"] + u["output"] >= cfg.monthly_token_limit:
            raise AIError("limit", "This month's AI token limit is used up. Raise it in Settings.", 429)

    try:
        text, tin, tout = _call(c, prompt, max_tokens)
    except AIError as e:
        AICall.objects.create(provider=c["provider"], model=c["model"], ok=False, error=e.message[:300])
        raise
    AICall.objects.create(provider=c["provider"], model=c["model"], input_tokens=tin or 0, output_tokens=tout or 0)
    if use_cache and text.strip():
        AICache.objects.update_or_create(key=key, defaults={"text": text})
    return {"text": text, "cached": False, "input": tin or 0, "output": tout or 0}
