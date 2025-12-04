# Performance Optimization Guide
## For Core i7 11th Gen, 32GB RAM, SSD (No GPU)

This guide outlines all available performance optimizations for your hardware configuration.

---

## 🚀 Quick Wins (Immediate Impact)

### 1. Install Optional Performance Dependencies

```powershell
# Install Numba for JIT compilation (2-5x speedup on hot loops)
pip install numba

# Install psutil for better CPU detection
pip install psutil

# Optional: Install Intel MKL-optimized NumPy (if using Intel Python)
# This can provide 2-3x speedup for linear algebra operations
# Already included if using Anaconda/Miniconda
```

**Expected Impact**: 2-5x faster HRV computations

### 2. Enable Parallel Processing

The app has parallel processing support but it's not fully enabled. See implementation below.

**Expected Impact**: 2-4x faster when processing multiple datasets

### 3. System-Level Optimizations

#### Windows Power Settings
- ✅ Already set to "Maximum Performance"
- Verify: `powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX` should show 100%

#### Python Process Priority
Add to your Streamlit startup script:
```python
import os
import psutil
# Set high priority for Python process
p = psutil.Process(os.getpid())
p.nice(psutil.HIGH_PRIORITY_CLASS)  # Windows
# p.nice(-10)  # Linux/Mac
```

#### Disable Windows Defender Real-Time Scanning (Temporary)
- Add Python/Streamlit directories to exclusions
- Or disable during analysis sessions

**Expected Impact**: 5-15% reduction in I/O latency

---

## 📊 Code-Level Optimizations

### 1. Parallel Windowed Analysis

Currently, windowed HRV analysis runs sequentially. With 4-8 cores, we can parallelize:

**Current**: Process dataset 1 → dataset 2 → dataset 3 (sequential)
**Optimized**: Process all datasets simultaneously (parallel)

**Expected Impact**: 2-4x faster for multiple datasets

### 2. Numba JIT Compilation

Hot loops in HRV calculations can be JIT-compiled:

- Entropy calculations (O(n²) → optimized)
- DFA calculations (vectorized)
- Poincaré analysis (vectorized)

**Expected Impact**: 2-3x faster for advanced metrics

### 3. Memory-Mapped I/O for Large Files

For datasets >100MB, use memory-mapped arrays:

```python
# Instead of loading entire file into RAM
rr_data = np.memmap('large_file.npy', dtype=np.float64, mode='r')
```

**Expected Impact**: Faster loading, lower memory footprint

### 4. Chunked Processing for Very Large Datasets

Process in chunks instead of loading everything:

**Current**: Load 1M RR intervals → process all
**Optimized**: Load 100K chunks → process → aggregate

**Expected Impact**: Lower memory usage, better cache locality

---

## 🔧 Streamlit-Specific Optimizations

### 1. Reduce Rerun Frequency

- Use `@st.fragment` for form inputs (already implemented)
- Use `st.session_state` for expensive computations (already implemented)
- Disable auto-rerun on widget changes where possible

### 2. Lazy Tab Loading

Only load tab content when tab is clicked:

```python
if st.session_state.get("tab_active") == "hrv":
    render_hrv_tab()
```

**Expected Impact**: Faster initial page load

### 3. Optimize Plot Rendering

- Downsample data before plotting (>5000 points)
- Use `st.plotly_chart` with `use_container_width=True` for responsive charts
- Cache plot configurations

**Expected Impact**: 50-70% faster plot rendering

---

## 💾 Database Optimizations

### 1. Connection Pooling

Already implemented with persistent connections.

### 2. Query Optimization

- Use indexed columns (already done)
- Batch inserts instead of one-by-one
- Use `PRAGMA optimize` periodically

### 3. WAL Mode

Already enabled for concurrent access.

---

## 📈 Expected Performance Gains

| Optimization | Impact | Difficulty | Priority |
|-------------|--------|------------|----------|
| Install Numba | 2-5x | Easy | ⭐⭐⭐⭐⭐ |
| Parallel Processing | 2-4x | Medium | ⭐⭐⭐⭐ |
| System Priority | 5-15% | Easy | ⭐⭐⭐ |
| Memory-Mapped I/O | 10-20% | Medium | ⭐⭐ |
| Chunked Processing | 15-30% | Hard | ⭐⭐ |
| Lazy Tab Loading | 30-50% | Easy | ⭐⭐⭐ |

---

## 🎯 Recommended Action Plan

### Phase 1: Quick Wins (30 minutes)
1. Install Numba: `pip install numba`
2. Install psutil: `pip install psutil`
3. Enable parallel processing (see implementation below)
4. Set Python process priority

**Expected Total Gain**: 3-6x faster

### Phase 2: Code Optimizations (2-4 hours)
1. Implement parallel windowed analysis
2. Add memory-mapped I/O for large files
3. Optimize plot rendering

**Expected Total Gain**: Additional 1.5-2x faster

### Phase 3: Advanced (Optional)
1. Chunked processing for very large datasets
2. Custom NumPy builds with MKL
3. Profile and optimize hot paths

**Expected Total Gain**: Additional 1.2-1.5x faster

---

## 🔍 Performance Monitoring

### Check Current Performance

```python
# In Performance Settings sidebar
# Click "📈 Show Performance Stats"
# Shows:
# - Cache hit rate
# - Slowest operations
# - Computation times
```

### Profile Bottlenecks

```python
# Add to app.py for profiling
import cProfile
profiler = cProfile.Profile()
profiler.enable()
# ... your code ...
profiler.disable()
profiler.dump_stats('profile.stats')
```

---

## 📝 Notes

- **32GB RAM**: You have plenty of headroom. Focus on CPU optimization.
- **SSD**: I/O is not a bottleneck. Focus on computation.
- **No GPU**: All optimizations are CPU-focused (correct approach).
- **Core i7 11th Gen**: 4-8 cores available. Parallel processing will help significantly.

---

## 🐛 Troubleshooting

### Numba Installation Issues
```powershell
# If Numba fails to install, try:
pip install numba --no-cache-dir
# Or use conda:
conda install numba
```

### Parallel Processing Not Working
- Check CPU core count: `python -c "import os; print(os.cpu_count())"`
- Verify multiprocessing is enabled in settings
- Check for GIL-bound operations (use threading for I/O, multiprocessing for CPU)

### Memory Issues
- Reduce `max_windows` in Performance Settings
- Enable `optimize_memory` in Performance Settings
- Use chunked processing for very large datasets

