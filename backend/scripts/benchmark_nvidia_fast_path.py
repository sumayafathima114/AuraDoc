"""Measure whether the configured NVIDIA model completes within one second.

Timeouts are reported as censored failures and are excluded from completion
latency percentiles. This script never prints prompts, output text, or secrets.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import replace
from datetime import datetime, timezone

import httpx

from app.ai.nvidia import NVIDIAProvider, _request_timeout
from app.core.config import settings

REQUEST_COUNT = 10
DEADLINE_SECONDS = 0.95


def percentile_nearest_rank(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


async def main() -> int:
    if not settings.nvidia_configured or not settings.nvidia_base_url:
        print("NVIDIA fast-path benchmark: CONFIGURATION_ERROR")
        return 1

    fast_config = replace(settings, nvidia_timeout_seconds=DEADLINE_SECONDS)
    completed_ms: list[int] = []
    timeouts = 0
    errors = 0
    print(f"Started at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"Model: {settings.nvidia_model}")
    print(f"Requests: {REQUEST_COUNT}; full-response deadline: {DEADLINE_SECONDS * 1000:.0f} ms")

    async with httpx.AsyncClient(
        timeout=_request_timeout(DEADLINE_SECONDS),
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
    ) as client:
        provider = NVIDIAProvider(config=fast_config, http_client=client)
        for index in range(1, REQUEST_COUNT + 1):
            request_started = asyncio.get_running_loop().time()
            try:
                result = await asyncio.wait_for(provider.diagnose(), timeout=DEADLINE_SECONDS)
            except TimeoutError:
                elapsed_ms = round((asyncio.get_running_loop().time() - request_started) * 1000)
                print(f"Request {index}: TOTAL_DEADLINE_TIMEOUT; elapsed={elapsed_ms} ms")
                timeouts += 1
                continue
            print(f"Request {index}: {result.category}; elapsed={result.elapsed_ms or 0} ms")
            if result.category == "SUCCESS" and result.elapsed_ms is not None:
                completed_ms.append(result.elapsed_ms)
            elif result.category in {"READ_TIMEOUT", "CONNECT_TIMEOUT", "POOL_TIMEOUT", "TIMEOUT"}:
                timeouts += 1
            else:
                errors += 1

    successes = len(completed_ms)
    print(f"Success rate: {successes}/{REQUEST_COUNT} ({successes / REQUEST_COUNT:.0%})")
    print(f"Timeout rate: {timeouts}/{REQUEST_COUNT} ({timeouts / REQUEST_COUNT:.0%})")
    print(f"Other errors: {errors}/{REQUEST_COUNT}")
    if completed_ms:
        print(f"Min complete response: {min(completed_ms)} ms")
        print(f"P50 complete response: {percentile_nearest_rank(completed_ms, 0.50)} ms")
        print(f"P95 complete response: {percentile_nearest_rank(completed_ms, 0.95)} ms")
        print(f"Max complete response: {max(completed_ms)} ms")
    else:
        print("Completion latency percentiles: NOT AVAILABLE (no complete responses)")
    return 0 if successes == REQUEST_COUNT and max(completed_ms) < 1000 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
