# NVIDIA provider validation

Validation notes updated 2026-10-06. Credential values, authorization headers, prompts, and generated text are intentionally omitted.

## Configured provider

- Base URL: `https://integrate.api.nvidia.com/v1`
- Model: `z-ai/glm-5.3-flash` (loaded from backend environment)
- Read timeout: 45 seconds; connect, write, and pool timeouts are bounded separately
- Client: asynchronous `httpx`; no retries
- The FastAPI process now owns a pooled client with keep-alive connections. Standalone diagnostics make a one-off request unless the benchmark script is used.

NVIDIA's official documentation lists the OpenAI-compatible `POST /v1/chat/completions` API, Bearer authentication, the configured model, `reasoning_effort`, and the GLM chat-template `clear_thinking` option. AuraDoc puts `clear_thinking` under `chat_template_kwargs`. Sources: [API reference](https://docs.api.nvidia.com/nim/reference/z-ai-glm-5-3-infer), [GLM-5.3-Flash model card](https://build.nvidia.com/z-ai/glm-5-3-flash/modelcard).

## Reported live diagnostic and current diagnosis

The user reported HTTP 200, 461 bytes, and 4,873 ms, classified as `MALFORMED_RESPONSE`. That metadata does not include the response body's safe structural shape, so the exact provider response format cannot be established. The current parser accepts non-empty OpenAI-compatible `choices[0].message.content` and selected structured text forms; it deliberately does not treat `reasoning_content` as the user-facing answer.

The prior smoke request capped output at 8 tokens and omitted model-specific reasoning settings. NVIDIA's GLM-5.3-Flash model card says reasoning defaults to `max`, `clear_thinking` defaults to false, and recommends `clear_thinking=true` for chat. This makes a reasoning budget consuming the tiny output cap a plausible code-side cause of an empty `message.content`, but it is not confirmed without a post-rotation live response. The diagnostic now uses the documented low-effort GLM options and 32 output tokens. A mocked regression test validates the request payload; live success remains unverified.

## Latency and connection reuse

The diagnostic measures total elapsed time, time to response headers, body read, and local JSON parsing separately. For its non-streaming request, time to headers includes network and provider/model wait; it is not a model-only measurement or streaming TTFT. HTTPX DNS/TCP/TLS and NVIDIA inference time are not independently separated by these measurements.

Production provider calls now reuse the FastAPI lifespan-owned HTTP client, avoiding a new TCP/TLS connection for each request when keep-alive is available. This can reduce repeat-request overhead but cannot guarantee sub-second inference. The one reported 4,873 ms result is pre-fix and not a post-fix benchmark.

Run one safe smoke request:

```powershell
cd "D:\mini project\AuraDoc\backend"
python -m scripts.diagnose_nvidia
```

Run a five-request sequential local/provider diagnostic benchmark:

```powershell
cd "D:\mini project\AuraDoc\backend"
python -m scripts.benchmark_nvidia
```

The benchmark stops at the first unsuccessful request, does not retry, and prints aggregate statistics only when all five requests succeed. It is a diagnostic sample, not a production performance benchmark.

## Live-test security status

Live validation and benchmarking are pending credential rotation. A secret was previously present in `backend/.env.example` and appeared in tool output. The example file has been replaced with placeholders, but the NVIDIA key and Supabase database password have **not** been rotated yet. Do not use the exposed values. Rotate them with their respective providers and update `backend/.env` locally before running either live command. No live result after the parser/connection changes has been verified.

## Offline regression validation

- Backend: `python -m pytest -q` — 59 passed, one pytest cache warning caused by the restricted workspace; the suite itself passed.
- Frontend: lint and `npx tsc --noEmit` passed.
- Production build: passed after rerunning outside the sandbox that first denied Next.js's TypeScript worker spawn (`spawn EPERM`).
- FastAPI lifespan-owned client and health endpoint: startup/shutdown passed; health returned HTTP 200. Live NVIDIA requests were not run because the previously exposed key has not been rotated.
- Security scan: no NVIDIA key/token pattern found in frontend source; `.env.example` files contain no credential values.
