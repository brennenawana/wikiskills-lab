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

The claude-cli backend accepts per-call `options` for agentic work:
  cwd, tools ("Bash", "Read", ...), max_turns, json_schema (dict),
  stream (True -> per-event trace list in the result), extra_env,
  timeout_s. Isolation flags are always on; --bare is forbidden (it turns
  off subscription login).

Credentials come from environment variables named in the config; values are
never written anywhere. Standard library only.
"""

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request

TRANSPORT_RETRY_STATUSES = {429, 500, 502, 503, 529}
RETRY_ATTEMPTS = 3

# Fresh, isolated CLI process per call: no session state, no memories, a
# fully replaced system prompt. Never --bare.
CLI_ISOLATION_ARGS = ["--safe-mode", "--disable-slash-commands",
                      "--strict-mcp-config", "--no-session-persistence"]


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


def _pick(entry, keys):
    for k in keys:
        v = entry.get(k)
        if isinstance(v, (int, float)):
            return v
    return 0


def extract_cli_usage(payload, model=None):
    """From a CLI result payload: sum EVERY modelUsage entry for billing;
    attribute tokens to the model under test (canonical-name match) when a
    model is given, else sum everything.

    Returns dict: tokens_in/out, cache_read/write, entry_usd (sum of every
    entry's own cost figure), reported_usd (the CLI's total)."""
    usage_map = payload.get("modelUsage") or payload.get("model_usage") or {}
    t_in = t_out = c_read = c_write = 0
    entry_usd = 0.0
    for key, entry in usage_map.items():
        if not isinstance(entry, dict):
            continue
        entry_usd += _pick(entry, ("costUSD", "cost_usd"))
        canonical = entry.get("canonicalModel") or entry.get(
            "canonical_model") or key
        if model and not str(canonical).startswith(model):
            continue
        t_in += _pick(entry, ("inputTokens", "input_tokens"))
        t_out += _pick(entry, ("outputTokens", "output_tokens"))
        c_read += _pick(entry, ("cacheReadInputTokens",
                                "cache_read_input_tokens"))
        c_write += _pick(entry, ("cacheCreationInputTokens",
                                 "cache_creation_input_tokens"))
    reported = payload.get("total_cost_usd") or payload.get("cost_usd") or 0.0
    return {"tokens_in": t_in, "tokens_out": t_out, "cache_read": c_read,
            "cache_write": c_write, "entry_usd": float(entry_usd),
            "reported_usd": float(reported)}


def parse_cli_result(stdout_text, prices=None, model=None):
    """Parse `claude -p --output-format json` output into a result dict.

    Billing = MAX of (CLI-reported total, per-entry cost sum,
    price-computed) — the highest of the independent accountings wins."""
    payload = json.loads(stdout_text)
    return _result_from_cli_payload(payload, prices, model)


def _result_from_cli_payload(payload, prices=None, model=None,
                             events=None):
    u = extract_cli_usage(payload, model)
    usage_model = model
    if usage_model is None:
        usage_map = payload.get("modelUsage") or {}
        usage_model = next(iter(usage_map), None)
    computed = _compute_usd(prices, usage_model, u["tokens_in"],
                            u["tokens_out"], u["cache_read"],
                            u["cache_write"]) or 0.0
    usd = max(u["reported_usd"], u["entry_usd"], computed)
    out = {"text": payload.get("result", ""), "model": usage_model,
           "tokens_in": u["tokens_in"], "tokens_out": u["tokens_out"],
           "cache_read": u["cache_read"], "cache_write": u["cache_write"],
           "usd": usd, "is_error": bool(payload.get("is_error")),
           "num_turns": payload.get("num_turns"),
           "subtype": payload.get("subtype")}
    if events is not None:
        out["events"] = events
    structured = payload.get("structured_output")
    if isinstance(structured, dict):
        out["structured"] = structured
    return out


def extract_json(result):
    """Best-effort JSON object from a gateway result: schema-forced
    structured output first, then the largest {...} block in the text."""
    if isinstance(result, dict):
        if isinstance(result.get("structured"), dict):
            return result["structured"]
        text = result.get("text") or ""
    else:
        text = str(result)
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        try:
            obj = json.loads(text[start:end + 1])
            return obj if isinstance(obj, dict) else None
        except ValueError:
            pass
    return None


class Gateway:
    def __init__(self, prices=None):
        self.prices = prices or {}

    def call(self, cfg, user_text, system=None, max_tokens=4096,
             options=None):
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
            return self._cli(cfg, user_text, system, options or {})
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

    def _cli(self, cfg, user_text, system, o):
        binary = cfg.get("command") or shutil.which("claude")
        if not binary:
            raise GatewayError("`claude` CLI not found on PATH")
        stream = bool(o.get("stream"))
        tools = o.get("tools", cfg.get("tools", ""))
        argv = [binary, "-p", user_text, *CLI_ISOLATION_ARGS,
                "--tools", tools, "--model", cfg["model"],
                "--output-format", "stream-json" if stream else "json"]
        if stream:
            argv += ["--verbose"]
        if system:
            argv += ["--system-prompt", system]
        if o.get("max_turns") is not None:
            argv += ["--max-turns", str(o["max_turns"])]
        if o.get("json_schema") is not None:
            argv += ["--json-schema", json.dumps(o["json_schema"])]
        if tools:
            argv += ["--permission-mode", "bypassPermissions"]
        argv += cfg.get("extra_args", [])

        env = os.environ.copy()
        env.update(o.get("extra_env") or {})
        timeout = o.get("timeout_s", cfg.get("timeout_s", 1800))

        last = ""
        for attempt in (1, 2, 3):
            try:
                proc = subprocess.run(argv, cwd=o.get("cwd"), env=env,
                                      capture_output=True, text=True,
                                      timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                raise GatewayError("CLI wall-clock timeout after %ss"
                                   % timeout) from exc
            events, payload = [], {}
            if stream:
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    events.append(obj)
                    if obj.get("type") == "result":
                        payload = obj
            else:
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {}

            # Retry ONLY transport/overload failures; a retried wrong answer
            # or refusal would bias results.
            status = payload.get("api_error_status")
            if payload and status not in TRANSPORT_RETRY_STATUSES:
                return _result_from_cli_payload(
                    payload, self.prices, cfg.get("model"),
                    events if stream else None)
            last = ("rc=%s api_error_status=%s stderr=%r"
                    % (proc.returncode, status, proc.stderr[:300]))
            if attempt < 3:
                time.sleep(15 * attempt)
        raise GatewayError("claude CLI failed after retries: %s" % last)
