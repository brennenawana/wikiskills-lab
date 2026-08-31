#!/usr/bin/env python3
"""Pluggable model gateway.

One `call()` for every way a model can be reached. The backend is chosen by
configuration, so the rest of the engine never cares where a model runs:

  {"kind": "openai",     "base_url": "http://127.0.0.1:11434/v1",
   "model": "qwen2.5-coder-32b", "api_key_env": null}
  {"kind": "anthropic",  "base_url": "https://api.anthropic.com",
   "model": "claude-haiku-4-5", "api_key_env": "ANTHROPIC_API_KEY"}
  {"kind": "claude-cli", "model": "claude-haiku-4-5"}   # subscription login
  {"kind": "canned",     "text": "ok"}                  # free dry runs

Metering doctrine baked in: sum EVERY usage entry a response reports, and
when several independent cost accountings exist, bill the HIGHEST. A single-
entry reading once undercounted real spend by ~30x.

Credentials come from environment variables named in the config; values are
never written anywhere. Standard library only.
"""

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request

TRANSPORT_RETRY_STATUSES = {429, 500, 502, 503, 529}
RETRY_ATTEMPTS = 3

# Flags that make every CLI call a fresh, isolated process: no session
# state, no memories, a fully replaced system prompt. Never use --bare
# (it turns off subscription login).
CLI_BASE_ARGS = ["--safe-mode", "--disable-slash-commands",
                 "--strict-mcp-config", "--no-session-persistence",
                 "--output-format", "json"]


class GatewayError(Exception):
    pass


def _compute_usd(prices, model, tokens_in, tokens_out, cache_read,
                 cache_write):
    if not prices or model not in prices:
        return None
    p = prices[model]
    usd = (tokens_in or 0) * p.get("in", 0) / 1e6 \
        + (tokens_out or 0) * p.get("out", 0) / 1e6 \
        + (cache_write or 0) * p.get("in", 0) * 1.25 / 1e6 \
        + (cache_read or 0) * p.get("in", 0) * 0.10 / 1e6
    return usd


def _http_json(url, payload, headers):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST")
    last_exc = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in TRANSPORT_RETRY_STATUSES \
                    and attempt < RETRY_ATTEMPTS - 1:
                last_exc = exc
                time.sleep(2 ** attempt)
                continue
            raise GatewayError("HTTP %d from %s: %s"
                               % (exc.code, url,
                                  exc.read()[:500])) from exc
        except OSError as exc:
            if attempt < RETRY_ATTEMPTS - 1:
                last_exc = exc
                time.sleep(2 ** attempt)
                continue
            raise GatewayError("cannot reach %s: %s" % (url, exc)) from exc
    raise GatewayError("retries exhausted: %s" % last_exc)


def _sum_usage_entries(usage_map):
    """Fold a {model: usage} map (CLI-style modelUsage) into totals.

    Sums across ALL entries; tolerant of both camelCase and snake_case.
    Returns (tokens_in, tokens_out, cache_read, cache_write, entry_usd_sum).
    """
    t_in = t_out = c_read = c_write = usd = 0
    names = {
        "in": ("inputTokens", "input_tokens", "prompt_tokens"),
        "out": ("outputTokens", "output_tokens", "completion_tokens"),
        "cr": ("cacheReadInputTokens", "cache_read_input_tokens"),
        "cw": ("cacheCreationInputTokens", "cache_creation_input_tokens"),
        "usd": ("costUSD", "cost_usd"),
    }

    def pick(entry, keys):
        for k in keys:
            v = entry.get(k)
            if isinstance(v, (int, float)):
                return v
        return 0

    for entry in usage_map.values():
        if not isinstance(entry, dict):
            continue
        t_in += pick(entry, names["in"])
        t_out += pick(entry, names["out"])
        c_read += pick(entry, names["cr"])
        c_write += pick(entry, names["cw"])
        usd += pick(entry, names["usd"])
    return t_in, t_out, c_read, c_write, usd


def parse_cli_result(stdout_text, prices=None):
    """Parse `claude -p --output-format json` output into a result dict.

    Applies both metering rules: sum every modelUsage entry; final usd is
    the MAX of (CLI-reported total, per-entry cost sum, price-computed).
    """
    data = json.loads(stdout_text)
    text = data.get("result", "")
    usage_map = data.get("modelUsage") or data.get("model_usage") or {}
    t_in, t_out, c_read, c_write, entry_usd = _sum_usage_entries(usage_map)
    reported = data.get("total_cost_usd") or data.get("cost_usd") or 0.0
    model = next(iter(usage_map), None)
    computed = _compute_usd(prices, model, t_in, t_out, c_read, c_write) or 0.0
    usd = max(float(reported), float(entry_usd), float(computed))
    return {"text": text, "model": model, "tokens_in": t_in,
            "tokens_out": t_out, "cache_read": c_read,
            "cache_write": c_write, "usd": usd,
            "is_error": bool(data.get("is_error"))}


class Gateway:
    def __init__(self, prices=None):
        self.prices = prices or {}

    def call(self, cfg, user_text, system=None, max_tokens=4096):
        kind = cfg.get("kind")
        if kind == "canned":
            return {"text": cfg.get("text", "ok"), "model": "canned",
                    "tokens_in": 0, "tokens_out": 0, "cache_read": 0,
                    "cache_write": 0, "usd": 0.0, "is_error": False}
        if kind == "openai":
            return self._openai(cfg, user_text, system, max_tokens)
        if kind == "anthropic":
            return self._anthropic(cfg, user_text, system, max_tokens)
        if kind == "claude-cli":
            return self._cli(cfg, user_text, system)
        raise GatewayError("unknown backend kind: %r" % kind)

    def _auth_header(self, cfg, header_name, prefix=""):
        env = cfg.get("api_key_env")
        if not env:
            return {}
        value = os.environ.get(env)
        if not value:
            raise GatewayError(
                "config names api_key_env=%s but that variable is not set "
                "(fail closed rather than call unauthenticated)" % env)
        return {header_name: prefix + value}

    def _openai(self, cfg, user_text, system, max_tokens):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_text})
        data = _http_json(
            cfg["base_url"].rstrip("/") + "/chat/completions",
            {"model": cfg["model"], "messages": messages,
             "max_tokens": max_tokens, "stream": False},
            self._auth_header(cfg, "Authorization", "Bearer "))
        usage = data.get("usage") or {}
        t_in = usage.get("prompt_tokens", 0)
        t_out = usage.get("completion_tokens", 0)
        c_read = (usage.get("prompt_tokens_details") or {}).get(
            "cached_tokens", 0)
        model = data.get("model", cfg["model"])
        text = ""
        choices = data.get("choices") or []
        if choices:
            text = (choices[0].get("message") or {}).get("content") or ""
        usd = _compute_usd(self.prices, model, t_in, t_out, c_read, 0) or 0.0
        return {"text": text, "model": model, "tokens_in": t_in,
                "tokens_out": t_out, "cache_read": c_read, "cache_write": 0,
                "usd": usd, "is_error": False}

    def _anthropic(self, cfg, user_text, system, max_tokens):
        payload = {"model": cfg["model"], "max_tokens": max_tokens,
                   "messages": [{"role": "user", "content": user_text}]}
        if system:
            payload["system"] = system
        headers = self._auth_header(cfg, "x-api-key")
        headers["anthropic-version"] = "2023-06-01"
        data = _http_json(cfg["base_url"].rstrip("/") + "/v1/messages",
                          payload, headers)
        usage = data.get("usage") or {}
        t_in = usage.get("input_tokens", 0)
        t_out = usage.get("output_tokens", 0)
        c_read = usage.get("cache_read_input_tokens", 0)
        c_write = usage.get("cache_creation_input_tokens", 0)
        model = data.get("model", cfg["model"])
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if isinstance(b, dict) and b.get("type") == "text")
        usd = _compute_usd(self.prices, model, t_in, t_out,
                           c_read, c_write) or 0.0
        return {"text": text, "model": model, "tokens_in": t_in,
                "tokens_out": t_out, "cache_read": c_read,
                "cache_write": c_write, "usd": usd, "is_error": False}

    def _cli(self, cfg, user_text, system):
        cmd = [cfg.get("command", "claude"), "-p", user_text,
               "--model", cfg["model"]] + CLI_BASE_ARGS
        if system:
            cmd += ["--system-prompt", system]
        for extra in cfg.get("extra_args", []):
            cmd.append(extra)
        last = None
        for attempt in range(RETRY_ATTEMPTS):
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=cfg.get("timeout_s", 900))
            if proc.returncode == 0 and proc.stdout.strip():
                result = parse_cli_result(proc.stdout, self.prices)
                status = _api_error_status(proc.stdout)
                if status in TRANSPORT_RETRY_STATUSES \
                        and attempt < RETRY_ATTEMPTS - 1:
                    time.sleep(2 ** attempt)
                    continue
                return result
            last = proc.stderr[:500]
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(2 ** attempt)
        raise GatewayError("claude CLI failed after retries: %s" % last)


def _api_error_status(stdout_text):
    m = re.search(r'"api_error_status"\s*:\s*(\d+)', stdout_text)
    return int(m.group(1)) if m else None
