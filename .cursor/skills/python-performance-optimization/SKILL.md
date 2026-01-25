---
name: python-performance-optimization
description: Profile, analyze, and optimize performance in Python (optimize performance, speed up, bottleneck, profiling) across CPU, memory, I/O, and database using reproducible measurement and profiling tools (cProfile/pstats, tracemalloc, py-spy). Use when the user reports slowness, high CPU, memory growth/leaks, slow queries, slow file/network I/O, or asks for performance tuning/optimization.
---

# Python Performance Optimization

## Quick start

When asked to “make it faster,” do this in order:

1. **Reproduce + baseline** the slow path with a representative input.
2. **Measure** with a stable timer (`time.perf_counter`) and enough iterations.
3. **Profile** (CPU and/or memory) to identify the *hot path*.
4. **Change one thing at a time**, re-measure, and keep correctness the same.

## Workflow (follow this sequence)

### 1) Define the performance goal

- **Metric**: latency, throughput, memory peak, CPU%, or I/O wait.
- **Target**: e.g., “P95 < 200 ms” or “peak RSS < 500 MB.”
- **Constraints**: correctness, numerical tolerance, determinism, platform, Python version.

### 2) Make measurement reliable

- Prefer `time.perf_counter()` for wall-clock timings.
- Use `timeit` for microbenchmarks; avoid `time.time()`.
- Run multiple iterations and report **min/median** (not just one run).
- Keep inputs realistic; avoid benchmarking on empty or tiny datasets.

### 3) Pick the right profiler

Choose the *smallest* tool that answers the question:

- **CPU (deterministic)**: `cProfile` + `pstats` to find the top cumulative time.
- **CPU (production / low overhead)**: `py-spy` sampling + flamegraph.
- **Line-by-line CPU**: `line_profiler` when one function is suspicious.
- **Memory / leaks**: `tracemalloc` snapshots; `memory_profiler` if available.

### 4) Diagnose before changing code

Look for:

- **Algorithmic issues**: \(O(n^2)\) loops, repeated scans, unnecessary sorting.
- **I/O amplification**: too many small reads/writes, per-row DB commits.
- **Redundant work**: repeated parsing/serialization, recomputing invariants.
- **Data structure mismatch**: list membership vs set/dict, copying large objects.

### 5) Apply optimizations in priority order

1. **Algorithm/data structure** changes (largest wins).
2. **Reduce Python overhead** on hot paths (move work out of loops, avoid repeated attribute lookups, leverage built-ins).
3. **Batch I/O and DB work** (fewer round-trips/commits).
4. **Vectorize** numeric workloads (NumPy/pandas) where appropriate.
5. **Cache** expensive pure computations (bounded caches).
6. **Parallelize** only when justified:
   - **CPU-bound**: multiprocessing.
   - **I/O-bound**: async or threading.
7. **Native extensions** for critical kernels (Cython/Rust/C) only if needed.

### 6) Verify + prevent regressions

- Re-run unit tests; add a regression test for the hotspot if possible.
- Benchmark before/after with the same inputs and environment.
- If you optimized memory, confirm peak usage and that growth is bounded.

## How to report results (use this structure)

- **Baseline**: what was measured and how (inputs, iterations, env).
- **Profile evidence**: top functions/lines and why they’re hot.
- **Root cause hypothesis**: algorithmic vs implementation vs I/O vs DB.
- **Proposed changes**: smallest safe change first; list trade-offs.
- **Verification plan**: tests + benchmark script/command.

## Additional resources

- Deeper commands and patterns: `reference.md`
- Ready-to-copy examples: `examples.md`

