# Harness: your own pipeline

A script or bot of your own that takes work (often a ticket) and hands it to
a model — for example: "take the JIRA ticket, send it to the agent, get a
branch back." Very common, and a strong case for observation.

## Recognize it

- The user describes a script, bot, or service of their own in stage 2.
  Ask where the model endpoint is configured and where the tracker
  credentials live (the places, never the values).

## What observation will look like (step 2)

- The pipeline already calls a model endpoint (a local server like Ollama or
  vLLM, or an API). Point that one setting at our recording proxy and every
  model call is **measured**: full request, response, tokens, cost, timing.
- The same applies to the tracker: route its API traffic through the proxy
  and what the pipeline pulled (whole tickets? every linked ticket? all
  comments?) is **measured** too.
- Result: usually the *most* observable harness of all, because everything
  passes through endpoints you control.

## Concretely

- Run one recording proxy per endpoint (`engine/recorder/proxy.py`): one for
  the model server, one for the tracker API. Change only the base URLs in
  the pipeline's config.
- Verify first, always: `python3 engine/recorder/probe.py proxy`, then the
  live canary in `steps/2-observe/probes.md`.

## Notes for later steps

- Improvement artifacts install as prompt text, pipeline configuration, and
  policy rules for what gets fetched and included.
