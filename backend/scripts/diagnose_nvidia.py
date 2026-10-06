"""Run one minimal NVIDIA request using backend-only configuration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.ai.nvidia import NVIDIAProvider


async def main() -> int:
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    provider = NVIDIAProvider()
    result = await provider.diagnose()
    print(f"Started at (UTC): {started_at}")
    print(f"NVIDIA diagnostic: {result.category}")
    print(f"Model: {provider.model_name or 'not configured'}")
    if result.elapsed_ms is not None:
        print(f"Total latency: {result.elapsed_ms} ms")
    if result.time_to_headers_ms is not None:
        print(f"Time to response headers: {result.time_to_headers_ms} ms")
    if result.body_read_ms is not None:
        print(f"Body read: {result.body_read_ms} ms")
    if result.parse_ms is not None:
        print(f"JSON parsing: {result.parse_ms} ms")
    if result.http_status is not None:
        print(f"HTTP status: {result.http_status}")
    if result.response_bytes is not None:
        print(f"Response size: {result.response_bytes} bytes")
    if result.exception_class is not None:
        print(f"Exception class: {result.exception_class}")
    if result.response_shape is not None:
        print(f"Safe response structure: {result.response_shape}")
    print(result.message)
    return 0 if result.category == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
