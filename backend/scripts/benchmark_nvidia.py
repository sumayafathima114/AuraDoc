"""Run up to five safe sequential NVIDIA smoke requests on one reused connection pool."""
from __future__ import annotations

import asyncio
import statistics
from datetime import datetime, timezone

import httpx

from app.ai.nvidia import NVIDIAProvider, _request_timeout
from app.core.config import settings


async def main() -> int:
    if not settings.nvidia_configured or not settings.nvidia_base_url:
        print("NVIDIA benchmark: CONFIGURATION_ERROR")
        return 1

    print(f"Started at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    latencies: list[int] = []
    async with httpx.AsyncClient(
        timeout=_request_timeout(settings.nvidia_timeout_seconds),
        limits=httpx.Limits(max_connections=2, max_keepalive_connections=1),
    ) as client:
        provider = NVIDIAProvider(http_client=client)
        for index in range(1, 6):
            result = await provider.diagnose()
            print(f"Request {index}: {result.category}; total={result.elapsed_ms} ms; status={result.http_status or 'none'}")
            if result.category != "SUCCESS" or result.elapsed_ms is None:
                print("Benchmark incomplete; stopped at the first unsuccessful provider request (no retry).")
                return 1
            latencies.append(result.elapsed_ms)

    print("NVIDIA local/provider diagnostic benchmark")
    print("Requests: 5")
    print(f"Min: {min(latencies)} ms")
    print(f"Median: {statistics.median(latencies):g} ms")
    print(f"Average: {statistics.fmean(latencies):.1f} ms")
    print(f"Max: {max(latencies)} ms")
    print("This is a local diagnostic sample, not a production performance benchmark.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
