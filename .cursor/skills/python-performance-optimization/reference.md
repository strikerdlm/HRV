# Reference: Commands, checklists, and patterns

## CPU profiling (cProfile / pstats)

### Profile a script (file output)

```bash
python -m cProfile -o profile.prof path/to/script.py
python -m pstats profile.prof
```

In `pstats`:

```
sort cumtime
stats 20
```

### Programmatic profiling (embed in code)

```python
import cProfile
import pstats
from pstats import SortKey

def main() -> None:
    # ... run the operation you want to profile ...
    pass

profiler = cProfile.Profile()
profiler.enable()
main()
profiler.disable()

stats = pstats.Stats(profiler).sort_stats(SortKey.CUMULATIVE)
stats.print_stats(20)
stats.dump_stats("profile.prof")
```

Interpretation tips:

- **cumtime**: total time spent in a function *including* callees (great for bottleneck discovery).
- **tottime**: time spent *inside* the function body (great for “this loop is slow”).
- Prefer optimizing functions that dominate **cumtime** and are hit frequently.

## Production / low-overhead CPU profiling (py-spy)

```bash
# See live hottest functions
py-spy top --pid 12345

# Record flamegraph for later inspection
py-spy record -o profile.svg --pid 12345

# Profile a script end-to-end
py-spy record -o profile.svg -- python path/to/script.py
```

## Line-level profiling (line_profiler)

```bash
pip install line-profiler
```

Annotate:

```python
@profile
def hot_function(data):
    # ...
    return data
```

Run:

```bash
kernprof -l -v path/to/script.py
```

## Memory profiling & leak triage

### tracemalloc snapshots (stdlib, recommended default)

```python
import tracemalloc

tracemalloc.start()
snapshot_before = tracemalloc.take_snapshot()

# ... run workload ...

snapshot_after = tracemalloc.take_snapshot()
top = snapshot_after.compare_to(snapshot_before, "lineno")
for stat in top[:20]:
    print(stat)
```

Notes:

- Use **“lineno”** grouping first to find the allocation site.
- If you need deeper attribution, switch to `"traceback"` (more expensive).

### memory_profiler (optional)

```bash
pip install memory-profiler
python -m memory_profiler path/to/script.py
```

## Measurement hygiene (avoid misleading benchmarks)

- Use `time.perf_counter()` for wall-clock measurement.
- Use `timeit` for microbenchmarks; ensure the work can’t be optimized away.
- Include warmup for JIT-like effects (e.g., disk cache, DB cache, imports).
- Benchmark the *hot path* with realistic inputs, not toy data.
- Report environment: Python version, OS, CPU, key dependency versions.

## Optimization decision tree (defaults)

### If CPU is high

- First: algorithm/data structure.
- Then: remove Python overhead in tight loops.
- Then: vectorize with NumPy/pandas when the operation is numeric and bulk.
- Only then: multiprocessing or native extensions.

### If latency is high but CPU is low

- Suspect I/O waits (network, disk) or DB queries.
- Batch operations; reduce round-trips; add indexes; use streaming.

### If memory grows over time

- Look for unbounded caches, global lists, accumulating DataFrames.
- Confirm object retention: references held in closures, globals, logging buffers.
- Bound caches (`lru_cache(maxsize=N)`, `deque(maxlen=N)`).

## High-signal code patterns

### Prefer built-ins and vectorized ops

- `sum(...)`, `min(...)`, `max(...)`, `sorted(...)`, `any(...)`, `all(...)`
- `str.join(...)` for concatenation in loops

### Use the right data structure

- Membership: `set`/`dict` over list
- Counters: `collections.Counter`
- Queues: `collections.deque`

### Batch I/O and DB work

- Prefer one big write over many small writes.
- Prefer one transaction over per-row commits.

## Database performance quick checks

- Use `EXPLAIN QUERY PLAN` (SQLite) to see if indexes are used.
- Add indexes for frequently filtered/joined columns.
- Avoid `SELECT *` on wide tables in hot paths; select only needed columns.

