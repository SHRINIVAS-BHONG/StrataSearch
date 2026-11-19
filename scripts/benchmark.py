#!/usr/bin/env python3
"""
StrataSearch Asynchronous Load Testing & Latency Benchmarking Script
Fires concurrent search queries against http://localhost:8000/api/v1/search
Measures p50, p95, and p99 latencies for both uncached and cached runs,
and prints a formatted Markdown benchmark table to the console.
"""

import argparse
import asyncio
import os
import random
import statistics
import sys
import time
from typing import List, Tuple

import httpx

DEFAULT_TARGET_URL = os.getenv("BENCHMARK_TARGET_URL", "http://localhost:8000/api/v1/search")
DEFAULT_NUM_REQUESTS = 500
DEFAULT_CONCURRENCY = 50

SAMPLE_TOPICS = [
    "distributed indexing architecture",
    "vector embeddings similarity search",
    "postgresql pgvector hnsw tuning",
    "reciprocal rank fusion algorithm",
    "redis semantic query caching",
    "celery asynchronous task workers",
    "tesseract optical character recognition",
    "inverted index full text search",
    "docker compose service orchestration",
    "high throughput low latency retrieval",
]


class BenchmarkRunner:
    def __init__(
        self,
        target_url: str = DEFAULT_TARGET_URL,
        num_requests: int = DEFAULT_NUM_REQUESTS,
        concurrency: int = DEFAULT_CONCURRENCY,
        timeout: float = 10.0,
    ):
        self.target_url = target_url
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.timeout = timeout

    async def _send_query(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",
    ) -> Tuple[bool, float, int]:
        """
        Sends a single POST request and measures latency in milliseconds.
        Returns: (success: bool, latency_ms: float, status_code: int)
        """
        payload = {
            "query": query,
            "top_k": top_k,
            "mode": mode,
        }
        async with semaphore:
            start_time = time.perf_counter()
            try:
                response = await client.post(
                    self.target_url,
                    json=payload,
                    timeout=self.timeout,
                )
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                success = response.status_code == 200
                return success, latency_ms, response.status_code
            except Exception:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                return False, latency_ms, 0

    async def run_batch(
        self,
        queries: List[str],
        phase_name: str,
    ) -> dict:
        """
        Executes a batch of queries concurrently and computes latency percentiles.
        """
        semaphore = asyncio.Semaphore(self.concurrency)
        limits = httpx.Limits(
            max_keepalive_connections=self.concurrency,
            max_connections=self.concurrency * 2,
        )

        print(f"\n[*] Executing {phase_name} phase ({len(queries)} queries, concurrency={self.concurrency})...")
        wall_start = time.perf_counter()

        async with httpx.AsyncClient(limits=limits) as client:
            tasks = [
                self._send_query(client, semaphore, q)
                for q in queries
            ]
            results = await asyncio.gather(*tasks)

        wall_duration = time.perf_counter() - wall_start

        latencies = [lat for success, lat, _ in results if success]
        success_count = sum(1 for success, _, _ in results if success)
        failure_count = len(results) - success_count

        if not latencies:
            print(f"[!] Warning: No successful responses received in {phase_name} phase.")
            return {
                "phase": phase_name,
                "total": len(queries),
                "success": 0,
                "failed": failure_count,
                "success_rate": 0.0,
                "rps": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "mean": 0.0,
                "wall_time_s": wall_duration,
            }

        latencies.sort()
        p50 = statistics.median(latencies)
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        mean_lat = statistics.mean(latencies)
        rps = success_count / wall_duration if wall_duration > 0 else 0.0

        return {
            "phase": phase_name,
            "total": len(queries),
            "success": success_count,
            "failed": failure_count,
            "success_rate": (success_count / len(queries)) * 100.0,
            "rps": rps,
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "mean": mean_lat,
            "wall_time_s": wall_duration,
        }

    async def benchmark(self) -> Tuple[dict, dict]:
        """
        Runs both uncached and cached benchmark suites.
        - Uncached: Unique queries per request (using UUID/random suffix)
        - Cached: Repetitive queries targeting pre-warmed cache keys
        """
        # Phase 1: Uncached Run (Unique queries to ensure cache misses)
        uncached_queries = [
            f"{random.choice(SAMPLE_TOPICS)} [unique-{i}-{time.time_ns()}]"
            for i in range(self.num_requests)
        ]
        uncached_results = await self.run_batch(uncached_queries, "Uncached (Cold Cache)")

        # Warm up cache with a fixed set of 5 distinct queries
        warmup_queries = [f"fixed benchmark query pattern {i}" for i in range(5)]
        semaphore = asyncio.Semaphore(5)
        async with httpx.AsyncClient() as client:
            warmup_tasks = [self._send_query(client, semaphore, q) for q in warmup_queries]
            await asyncio.gather(*warmup_tasks)

        # Phase 2: Cached Run (Queries repeating the 5 pre-warmed keys)
        cached_queries = [
            warmup_queries[i % len(warmup_queries)]
            for i in range(self.num_requests)
        ]
        cached_results = await self.run_batch(cached_queries, "Cached (Warm Cache)")

        return uncached_results, cached_results


def print_markdown_report(uncached: dict, cached: dict):
    """
    Renders formatted Markdown benchmark table and summary statistics.
    """
    p50_speedup = (
        f"{uncached['p50'] / cached['p50']:.2f}x"
        if cached.get("p50", 0) > 0 and uncached.get("p50", 0) > 0
        else "N/A"
    )
    rps_speedup = (
        f"{cached['rps'] / uncached['rps']:.2f}x"
        if uncached.get("rps", 0) > 0 and cached.get("rps", 0) > 0
        else "N/A"
    )

    markdown_output = f"""
# ==============================================================================
# StrataSearch Load Testing & Latency Benchmark Report
# Target: {DEFAULT_TARGET_URL} | Total Queries per Phase: {uncached['total']}
# ==============================================================================

### Benchmark Summary Table

| Phase | Total Requests | Success Rate | RPS (Throughput) | p50 (ms) | p95 (ms) | p99 (ms) | Mean (ms) | Duration (s) |
|---|---|---|---|---|---|---|---|---|
| **{uncached['phase']}** | {uncached['total']} | {uncached['success_rate']:.1f}% | {uncached['rps']:.1f} req/s | {uncached['p50']:.2f} ms | {uncached['p95']:.2f} ms | {uncached['p99']:.2f} ms | {uncached['mean']:.2f} ms | {uncached['wall_time_s']:.2f} s |
| **{cached['phase']}** | {cached['total']} | {cached['success_rate']:.1f}% | {cached['rps']:.1f} req/s | {cached['p50']:.2f} ms | {cached['p95']:.2f} ms | {cached['p99']:.2f} ms | {cached['mean']:.2f} ms | {cached['wall_time_s']:.2f} s |

### Key Performance Insights
- **Cache Hit Latency Gain (p50):** {p50_speedup} latency reduction on warm cache hits.
- **Throughput Scaling:** {rps_speedup} throughput improvement when leveraging Redis query caching.
- **99th Percentile Tail Latency:** Uncached p99 = {uncached['p99']:.2f} ms vs Cached p99 = {cached['p99']:.2f} ms.
"""
    print(markdown_output)


async def main():
    parser = argparse.ArgumentParser(description="StrataSearch Asynchronous Load & Latency Benchmark")
    parser.add_argument("--url", type=str, default=DEFAULT_TARGET_URL, help="Target search endpoint URL")
    parser.add_argument("-n", "--requests", type=int, default=DEFAULT_NUM_REQUESTS, help="Number of queries per phase")
    parser.add_argument("-c", "--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Concurrent HTTP worker limit")
    parser.add_argument("-t", "--timeout", type=float, default=10.0, help="Per-request HTTP timeout in seconds")
    args = parser.parse_args()

    runner = BenchmarkRunner(
        target_url=args.url,
        num_requests=args.requests,
        concurrency=args.concurrency,
        timeout=args.timeout,
    )

    uncached, cached = await runner.benchmark()
    print_markdown_report(uncached, cached)


if __name__ == "__main__":
    asyncio.run(main())
