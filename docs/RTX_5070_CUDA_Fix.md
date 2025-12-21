# RTX 5070 (Blackwell) CUDA Toolkit Fix Guide

**Issue**: `CUDA_ERROR_NO_BINARY_FOR_GPU` - PATH points to wrong CUDA version + wrong CuPy package

**Date**: 2025-12-20  
**GPU**: NVIDIA GeForce RTX 5070 (Blackwell, Compute Capability 12.0)

---

## Problem Summary

Your RTX 5070 GPU is detected, but kernel compilation fails because:

- ✅ **CUDA Toolkit 13.1**: Installed (supports Blackwell CC 12.0)
- ⚠️ **PATH Issue**: Environment variables point to CUDA 12.5 instead of 13.1
- ⚠️ **CuPy Version**: Currently using `cupy-cuda12x` (for CUDA 12.x), need `cupy-cuda13x` (for CUDA 13.x)
- **Error**: `CUDA_ERROR_NO_BINARY_FOR_GPU: no kernel image is available for execution on the device`

**Root Cause**: Even though CUDA 13.1 is installed, your PATH points to CUDA 12.5, and CuPy is using the wrong package variant. You need to:
1. Update PATH to point to CUDA 13.1
2. Install `cupy-cuda13x` instead of `cupy-cuda12x`

---

## Solution: Update PATH and Install Correct CuPy Version

### Step 1: Verify CUDA 13.1 Installation

```powershell
# Check if CUDA 13.1 is installed
Test-Path "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
# Should return: True

# Check current PATH (likely points to 12.5)
$env:PATH -split ';' | Select-String "CUDA"
# Currently shows: ...\CUDA\v12.5\bin

# Check current CuPy version
pip list | Select-String "cupy"
# Currently shows: cupy-cuda12x 13.6.0
```

### Step 2: Update Environment Variables

**Method 1: Windows GUI (Permanent - Recommended)**

1. **Open Environment Variables**:
   - Press `Win + X` → System → Advanced system settings
   - Or: Windows Settings → System → About → Advanced system settings
   - Click "Environment Variables" button

2. **Update `CUDA_PATH`**:
   - Under "User variables" or "System variables", find `CUDA_PATH`
   - If it exists and points to `v12.5`, edit it
   - If it doesn't exist, click "New"
   - Set value to: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1`

3. **Update `PATH`**:
   - Find `PATH` in the same list
   - Click "Edit"
   - **Remove** any entries pointing to CUDA 12.5:
     - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin`
     - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\libnvvp`
   - **Add** these entries (or use `%CUDA_PATH%` variable):
     - `%CUDA_PATH%\bin` (or `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin`)
     - `%CUDA_PATH%\libnvvp` (or `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\libnvvp`)
   - **Important**: Move CUDA 13.1 entries to the **top** of the PATH list (higher priority)

4. **Click OK** on all dialogs

**Method 2: PowerShell (Current Session Only - For Testing)**

```powershell
# Set for current PowerShell session
$env:CUDA_PATH = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
$env:PATH = "$env:CUDA_PATH\bin;$env:CUDA_PATH\libnvvp;" + ($env:PATH -replace ".*CUDA\\v12\.5[^;]*;?", "")

# Verify
nvcc --version
# Should now show: release 13.1, V13.1.x
```

### Step 3: Install Correct CuPy Version for CUDA 13.1

The current `cupy-cuda12x` package is built for CUDA 12.x. For CUDA 13.1, you need `cupy-cuda13x`:

```powershell
# Uninstall current CuPy
pip uninstall cupy-cuda12x -y

# Install CuPy for CUDA 13.x
pip install cupy-cuda13x
```

**Verify installation**:
```powershell
pip list | Select-String "cupy"
# Should show: cupy-cuda13x 13.6.0
```

### Step 4: Verify PATH Update

```powershell
# Check CUDA_PATH
$env:CUDA_PATH
# Should show: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1

# Check PATH includes CUDA 13.1 bin (not 12.5)
$env:PATH -split ';' | Select-String "CUDA"
# Should include: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin
# Should NOT include: ...\CUDA\v12.5\bin

# Verify nvcc points to 13.1
nvcc --version
# Should show: release 13.1, V13.1.x (not 12.5)
```

### Step 5: Restart and Test

1. **Restart your computer** (REQUIRED for permanent PATH changes to take effect)
2. **Restart Streamlit app**
3. **Check GPU status** in the app sidebar under "🖥️ GPU Processing"

You should now see:
```
✓ NVIDIA GeForce RTX 5070
VRAM: X.X/11.9 GB free
CUDA 13.1 | CC 12.0
✓ GPU acceleration active
```

**Test CuPy directly**:
```powershell
python -c "import cupy as cp; x = cp.array([1,2,3]); print('Mean:', float(cp.mean(x))); print('✅ GPU kernel compilation works!')"
```

**Note**: If you only updated PATH in PowerShell (Method 2), you'll need to restart your computer for the changes to persist. The PowerShell method is only for testing.

---

## Alternative: Use CUDA 12.5 with CPU Fallback

If you cannot update PATH or install `cupy-cuda13x` right now:

- **The app works perfectly without GPU acceleration**
- All HRV computations automatically fall back to CPU (NumPy)
- Performance is still excellent for typical dataset sizes
- GPU acceleration mainly benefits very large datasets (100k+ RR intervals)

**No action needed** - the app will automatically use CPU when GPU is unavailable.

---

## Technical Details

### Why Both PATH and CuPy Package Matter

- **CUDA Toolkit 13.1** includes the compiler (`nvcc`) and runtime libraries needed for Blackwell (CC 12.0)
- **PATH** tells the system where to find `nvcc` and DLLs
- **CuPy package variant** (`cupy-cuda13x` vs `cupy-cuda12x`) determines which CUDA version CuPy is built against
- Even with CUDA 13.1 installed, if PATH points to 12.5, CuPy can't find the right compiler
- Even with PATH correct, if `cupy-cuda12x` is installed, it may not have pre-compiled kernels for sm_120

### Version Compatibility Matrix

| GPU Architecture | Compute Capability | CUDA Toolkit Required | CuPy Package |
|------------------|-------------------|----------------------|--------------|
| Blackwell (RTX 50xx) | 12.0 | **13.1** (or 12.8+) | `cupy-cuda13x` |
| Ada Lovelace (RTX 40xx) | 8.9 | 12.0+ | `cupy-cuda12x` |
| Ampere (RTX 30xx) | 8.6 | 11.0+ | `cupy-cuda11x` or `cupy-cuda12x` |
| Turing (RTX 20xx) | 7.5 | 10.0+ | `cupy-cuda11x` |

### Current System Status

- ✅ **NVIDIA Driver**: 591.44 (supports CUDA 13.1)
- ⚠️ **CuPy**: 13.6.0 (cupy-cuda12x) - Need to switch to cupy-cuda13x
- ✅ **CUDA Toolkit**: 13.1 installed (supports Blackwell)
- ⚠️ **PATH Issue**: Points to CUDA 12.5 instead of 13.1
- ✅ **GPU Hardware**: RTX 5070 detected

---

## Troubleshooting

### Issue: "nvcc not found" after updating PATH

**Solution**: Verify PATH was updated correctly:
```powershell
$env:PATH -split ';' | Select-String "CUDA"
# Should show v13.1, not v12.5
```

If still not found, restart your computer (PATH changes require restart).

### Issue: Multiple CUDA versions conflict

**Solution**: The app uses the CUDA version found first in PATH. Ensure CUDA 13.1 is at the top:
1. Edit PATH environment variable
2. Move CUDA 13.1 entries above CUDA 12.5 entries
3. Restart computer

### Issue: Still getting "no kernel image" errors after installing cupy-cuda13x

**Solutions**:
1. **Verify PATH points to CUDA 13.1** (not 12.5)
2. **Restart computer** (ensures DLLs are loaded from correct location)
3. **Reinstall CuPy**:
   ```powershell
   pip uninstall cupy-cuda13x -y
   pip install cupy-cuda13x --no-cache-dir
   ```
4. **Check CuPy can find CUDA**:
   ```powershell
   python -c "import cupy as cp; print('CUDA found:', cp.cuda.is_available())"
   ```

### Issue: "cupy-cuda13x not found" when installing

**Solution**: `cupy-cuda13x` is available from CuPy 13.6.0+. If you get an error:
```powershell
# Try installing latest version explicitly
pip install cupy-cuda13x>=13.6.0

# Or install from GitHub (if PyPI doesn't have it yet)
pip install git+https://github.com/cupy/cupy.git@v13.6.0#subdirectory=python
```

---

## Verification Commands

After updating PATH and installing `cupy-cuda13x`, verify everything works:

```powershell
# 1. Check CUDA Toolkit version (should be 13.1)
nvcc --version
# Expected: release 13.1, V13.1.x

# 2. Check PATH points to 13.1
$env:PATH -split ';' | Select-String "CUDA"
# Should show: ...\CUDA\v13.1\bin

# 3. Check CuPy version
pip list | Select-String "cupy"
# Should show: cupy-cuda13x 13.6.0

# 4. Check GPU detection
python -c "from app.gpu_processing import get_gpu_info; info = get_gpu_info(refresh=True); print(f'GPU: {info.device_name}'); print(f'Available: {info.available}'); print(f'CUDA: {info.cuda_version}')"

# 5. Test CuPy kernel compilation
python -c "import cupy as cp; x = cp.array([1,2,3]); print('Mean:', float(cp.mean(x))); print('✅ GPU kernel compilation works!')"
```

---

## References

- [NVIDIA CUDA Toolkit Downloads](https://developer.nvidia.com/cuda-downloads)
- [CuPy Installation Guide](https://docs.cupy.dev/en/stable/install.html)
- [CuPy Releases (cupy-cuda13x)](https://github.com/cupy/cupy/releases)
- [Blackwell Compatibility Guide](https://docs.nvidia.com/cuda/blackwell-compatibility-guide/)

---

**Last Updated**: 2025-12-20
