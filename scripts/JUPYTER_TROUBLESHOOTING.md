# Jupyter Notebook Troubleshooting Guide

## Quick Diagnosis

Run the diagnostic script to check your setup:

```powershell
cd scripts
python diagnose_jupyter.py
```

For automatic fixes:

```powershell
python diagnose_jupyter.py --fix
```

## Common Issues and Solutions

### Issue 1: Kernel Won't Start

**Symptoms:**
- Error: "Failed to start the Kernel 'Valquiria Space Analog Analysis'"
- Kernel shows as "Connecting..." but never connects
- Kernel dies immediately after starting

**Solutions:**

1. **Reinstall the kernel:**
   ```powershell
   cd scripts
   .\fix_jupyter_kernel.ps1
   ```

2. **Manually reinstall using stats environment:**
   ```powershell
   & "C:\Users\User\Miniconda3\envs\stats\python.exe" -m ipykernel install --user --name=valquiria-analysis --display-name="Valquiria Space Analog Analysis"
   ```

3. **Verify kernel is using correct Python:**
   ```powershell
   python -m jupyter kernelspec list
   ```
   Check that `valquiria-analysis` points to the stats environment Python.

4. **Select the correct kernel in the notebook:**
   - In Jupyter: Kernel -> Change Kernel -> "Valquiria Space Analog Analysis"
   - In VS Code: Click kernel selector in top right, choose "Valquiria Space Analog Analysis"

### Issue 2: Missing Dependencies

**Symptoms:**
- ImportError when running cells
- "ModuleNotFoundError: No module named 'X'"

**Solutions:**

1. **Install dependencies in stats environment:**
   ```powershell
   & "C:\Users\User\Miniconda3\envs\stats\python.exe" -m pip install -r scripts/requirements_jupyter.txt
   ```

2. **Install specific missing package:**
   ```powershell
   & "C:\Users\User\Miniconda3\envs\stats\python.exe" -m pip install <package-name>
   ```

3. **Verify installation:**
   ```powershell
   & "C:\Users\User\Miniconda3\envs\stats\python.exe" -c "import numpy, pandas, scipy, matplotlib, seaborn; print('OK')"
   ```

### Issue 3: Wrong Python Version

**Symptoms:**
- Notebook metadata shows Python 3.13.2 but you have 3.12.9
- Version mismatch warnings

**Solutions:**

1. **The notebook is configured for Python 3.13.2 in the stats environment, which is correct.**
2. **If you want to use a different Python version, update the notebook metadata:**
   ```python
   # Run diagnose_jupyter.py --fix to automatically update
   ```

### Issue 4: Kernel Timeout

**Symptoms:**
- Kernel takes too long to start
- "Kernel timeout" errors

**Solutions:**

1. **Increase timeout in Jupyter settings**
2. **Check if stats environment Python is accessible:**
   ```powershell
   & "C:\Users\User\Miniconda3\envs\stats\python.exe" --version
   ```

3. **Restart Jupyter server completely**

### Issue 5: File Not Found Errors

**Symptoms:**
- "FileNotFoundError: '2025-11-06 00-50-07.txt'"
- Data loading fails

**Solutions:**

1. **Check file path in notebook:**
   - The notebook looks for `2025-11-06 00-50-07.txt` in the current directory
   - Ensure the file exists in the same directory as the notebook

2. **Update the file path in the notebook:**
   ```python
   rr_file_path = 'path/to/your/file.txt'  # Update this line
   ```

3. **Use absolute path if needed:**
   ```python
   rr_file_path = r'C:\Users\User\OneDrive\FAC\Research\Python Scripts\HRV\2025-11-06 00-50-07.txt'
   ```

## Environment Setup

### Verify Stats Environment

```powershell
# Check if stats environment exists
conda env list

# Activate stats environment
conda activate stats

# Verify Python version
python --version  # Should be 3.13.2

# Check dependencies
python -c "import numpy, pandas, scipy, matplotlib, seaborn, jupyter, ipykernel; print('All OK')"
```

### Install/Update Dependencies

```powershell
# Activate stats environment
conda activate stats

# Install from requirements file
pip install -r scripts/requirements_jupyter.txt

# Or install individually
pip install numpy pandas scipy matplotlib seaborn jupyter notebook ipykernel
```

## Kernel Configuration

### Current Configuration

- **Kernel Name:** `valquiria-analysis`
- **Display Name:** "Valquiria Space Analog Analysis"
- **Python:** `C:\Users\User\Miniconda3\envs\stats\python.exe`
- **Python Version:** 3.13.2

### Kernel Location

```
C:\Users\User\AppData\Roaming\jupyter\kernels\valquiria-analysis\kernel.json
```

### View Kernel Config

```powershell
type "$env:APPDATA\jupyter\kernels\valquiria-analysis\kernel.json"
```

## Testing Your Setup

1. **Run diagnostic:**
   ```powershell
   python scripts/diagnose_jupyter.py
   ```

2. **Test kernel directly:**
   ```powershell
   & "C:\Users\User\Miniconda3\envs\stats\python.exe" -m ipykernel --version
   ```

3. **Start Jupyter and test:**
   ```powershell
   jupyter notebook
   ```
   - Open the notebook
   - Select kernel: Kernel -> Change Kernel -> "Valquiria Space Analog Analysis"
   - Run first cell

## Getting Help

If issues persist:

1. **Check Jupyter server logs** for detailed error messages
2. **Run diagnostic script** with verbose output
3. **Verify all paths** are correct (Python, kernel, notebook)
4. **Check file permissions** (especially for OneDrive sync)
5. **Try restarting** Jupyter server and kernel

## Quick Fix Checklist

- [ ] Run `python scripts/diagnose_jupyter.py`
- [ ] Run `.\scripts\fix_jupyter_kernel.ps1`
- [ ] Verify stats environment exists and has Python 3.13.2
- [ ] Install dependencies: `pip install -r scripts/requirements_jupyter.txt`
- [ ] Restart Jupyter server
- [ ] Select correct kernel in notebook
- [ ] Check file paths in notebook cells
- [ ] Verify data files exist

