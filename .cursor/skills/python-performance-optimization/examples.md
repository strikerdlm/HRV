# Examples: Copy/paste workflows

## Example 1: “This script is slow” (CPU hotspot)

1) Record a CPU profile:

```bash
python -m cProfile -o profile.prof path/to/script.py
python -m pstats profile.prof
```

2) In `pstats`, find the hot path:

```
sort cumtime
stats 25
```

3) Optimization loop:

- Pick the top 1–2 functions by **cumtime**
- Improve algorithm/data structure first
- Re-run the profile and confirm the hotspot moved or shrank

## Example 2: Microbenchmark a suspected hot function

```python
import timeit

def candidate(n: int) -> int:
    return sum(i * 2 + 1 for i in range(n))

n = 200_000
sec = timeit.timeit(lambda: candidate(n), number=50)
print(f"median-ish avg: {sec/50:.6f} s")
```

Tips:

- Keep the same `n` across runs.
- Increase `number` until total runtime is at least ~1–2 seconds.

## Example 3: Memory growth triage (tracemalloc)

```python
import tracemalloc

def workload() -> None:
    # ... run the part of the program that grows memory ...
    pass

tracemalloc.start()
before = tracemalloc.take_snapshot()

workload()

after = tracemalloc.take_snapshot()
top = after.compare_to(before, "lineno")
print("Top allocations:")
for stat in top[:15]:
    print(stat)
```

Next steps:

- Inspect the top allocation sites.
- Look for containers that grow without bounds (lists, dicts, DataFrames).
- Bound caches and remove unintended retained references.

## Example 4: Batch SQLite inserts (transaction)

```python
import sqlite3
from typing import Iterable

def insert_users(conn: sqlite3.Connection, names: Iterable[str]) -> None:
    rows = [(name,) for name in names]
    with conn:  # single transaction
        conn.executemany("INSERT INTO users(name) VALUES (?)", rows)
```

Why this is faster:

- Fewer commits (one transaction) reduces fsync overhead.
- `executemany` reduces Python↔SQLite call overhead.

## Example 5: Replace list membership with set membership

```python
from typing import Iterable

def filter_known(items: Iterable[str], known: Iterable[str]) -> list[str]:
    known_set = set(known)
    return [x for x in items if x in known_set]
```

When it helps:

- Hot code does repeated membership checks.
- `known` is non-trivial in size and reused.

## Example 6: Safe, bounded caching for an expensive pure helper

```python
from functools import lru_cache

@lru_cache(maxsize=2048)
def normalize_id(raw: str) -> str:
    # Example placeholder: expensive parsing/normalization
    return raw.strip().lower()
```

Checklist:

- Cache only functions that are **pure** (same input → same output).
- Always **bound** cache size unless you can prove the key space is bounded.

