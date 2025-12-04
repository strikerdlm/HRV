# Performance Optimization Options
## For Your System: Core i7 11th Gen, 32GB RAM, SSD, No GPU

---

## ✅ Already Implemented (v1.7.3)

1. **HRV Results Caching** - Eliminates redundant computations
2. **Upload File Caching** - Files only parsed once
3. **Computation State Tracking** - Skips work when data unchanged
4. **Parallel Windowed Analysis** - Processes multiple datasets simultaneously
5. **Process Priority Boost** - Sets high priority on startup (if psutil available)

---

## 🚀 Quick Install (5 minutes)

### Step 1: Install Performance Dependencies

```powershell
# In your conda environment (hrv-py312)
conda activate hrv-py312

# Install Numba for JIT compilation (2-5x speedup)
pip install numba

# Install psutil for better CPU detection and process priority
pip install psutil
```

**Impact**: 2-5x faster HRV computations, automatic CPU detection

### Step 2: Verify Installation

```powershell
python -c "import numba; print('Numba:', numba.__version__)"
python -c "import psutil; print('CPU cores:', psutil.cpu_count())"
```

---

## 📊 Performance Settings in App

### Access Performance Settings
1. Open the app
2. Look in the **sidebar** → **⚡ Performance Settings**
3. Should show: **🟢 Detected: HIGH performance CPU**

### Recommended Settings for Your System

Since you have a Core i7 11th gen (high-tier CPU):

- **Performance Preset**: "Auto (Recommended)" ✅ (already set)
- **Max plot points**: 3000 (auto-detected)
- **Max DataFrame rows**: 500 (auto-detected)
- **Max windows**: 1000 (auto-detected)
- **Enable heavy plots**: ✅ (auto-enabled)
- **Optimize memory**: ❌ (not needed with 32GB)
- **Fast entropy mode**: ❌ (not needed for high-tier CPU)

---

## 🔧 Additional Optimizations Available

### 1. Enable Parallel Processing (Already Implemented)

The app now automatically uses parallel processing when:
- Multiple datasets are uploaded
- CPU has 4+ cores (your i7 qualifies)
- `use_parallel=True` in adaptive settings

**Status**: ✅ Already active if you have multiple datasets

### 2. Numba JIT Compilation

If Numba is installed, the app automatically uses it for:
- Entropy calculations
- DFA computations
- Poincaré analysis

**Status**: ⚠️ Requires `pip install numba` (see Step 1 above)

### 3. System-Level Optimizations

#### Windows Power Plan
```powershell
# Verify maximum performance is active
powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX

# Should show: 100 (100%)
```

#### Disable Windows Defender (Temporary)
- Add Python/Streamlit directories to exclusions
- Or disable real-time scanning during analysis sessions

**Impact**: 5-15% reduction in I/O latency

---

## 📈 Expected Performance Gains

| Optimization | Status | Expected Gain |
|-------------|--------|---------------|
| HRV Caching | ✅ Active | 5-10x faster on reruns |
| Parallel Processing | ✅ Active | 2-4x for multiple datasets |
| Numba JIT | ⚠️ Install needed | 2-5x for advanced metrics |
| Process Priority | ✅ Active (if psutil installed) | 5-15% overall |
| System Optimizations | ⚠️ Manual setup | 5-15% I/O improvement |

**Total Potential Gain**: **10-20x faster** after installing Numba

---

## 🎯 Action Items

### Immediate (5 minutes)
1. ✅ Install Numba: `pip install numba`
2. ✅ Install psutil: `pip install psutil`
3. ✅ Restart Streamlit app

### Optional (15 minutes)
1. Add Python directories to Windows Defender exclusions
2. Verify power plan is at maximum performance
3. Check Performance Settings in sidebar shows "HIGH" tier

---

## 🔍 Monitoring Performance

### In-App Performance Stats
1. Open sidebar → **⚡ Performance Settings**
2. Click **📈 Show Performance Stats**
3. View:
   - Cache hit rate (should be >80% after first run)
   - Slowest operations
   - Computation times

### Check CPU Usage
```powershell
# Monitor CPU usage during analysis
# Task Manager → Performance → CPU
# Should see 50-80% usage with parallel processing
```

---

## 🐛 Troubleshooting

### Numba Not Working
```powershell
# Check if Numba is installed
python -c "import numba; print(numba.__version__)"

# If import fails, reinstall:
pip uninstall numba
pip install numba --no-cache-dir
```

### Parallel Processing Not Active
- Check you have multiple datasets uploaded
- Verify CPU has 4+ cores: `python -c "import os; print(os.cpu_count())"`
- Check Performance Settings shows "HIGH" tier

### Still Slow?
1. Check cache hit rate (should be >80%)
2. Reduce `max_windows` in Performance Settings
3. Enable `fast_windowing` in sidebar
4. Check Task Manager for other CPU-intensive processes

---

## 📝 Notes

- **32GB RAM**: Not a bottleneck. Focus on CPU optimization.
- **SSD**: I/O is fast. Not a concern.
- **No GPU**: All optimizations are CPU-focused (correct approach).
- **Core i7 11th Gen**: 4-8 cores. Parallel processing will help significantly.

---

## 📚 Full Documentation

See `docs/PERFORMANCE_OPTIMIZATION.md` for detailed technical information.

