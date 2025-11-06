# Conda libmamba-solver Fix Summary

## Issue
Conda was failing with the error:
```
Error while loading conda entry point: conda-libmamba-solver (module 'libmambapy' has no attribute 'QueryFormat')
```

This is caused by a version incompatibility between conda and the conda-libmamba-solver plugin.

## Fix Applied

1. **Uninstalled conda-libmamba-solver plugin**
   - Removed the problematic plugin package

2. **Updated conda configuration**
   - Set solver to "classic" in `~/.condarc`
   - Created backup of original config at `~/.condarc.backup`

## Next Steps

### IMPORTANT: Restart Your Terminal

The fix requires a **fresh terminal session** to take effect. The error will continue to appear in the current session because the plugin was already loaded.

1. **Close your current PowerShell/terminal window**
2. **Open a new terminal**
3. **Test conda:**
   ```powershell
   conda --version
   ```
   Should show: `conda 24.11.3` (without the error)

4. **List environments:**
   ```powershell
   conda env list
   ```
   Should list all environments without errors

### If Issues Persist After Restart

1. **Clear conda cache:**
   ```powershell
   conda clean --all
   ```

2. **Update conda:**
   ```powershell
   conda update conda
   ```

3. **Manually verify config:**
   ```powershell
   type $env:USERPROFILE\.condarc
   ```
   Should show: `solver: classic`

4. **If still broken, reinstall conda:**
   ```powershell
   # This is a last resort
   conda install -n base conda --force-reinstall
   ```

## Verification

After restarting your terminal, run:

```powershell
# Should work without errors
conda --version
conda env list
conda info

# Activate stats environment (for Jupyter)
conda activate stats
python --version  # Should be 3.13.2
```

## What Changed

- **Before:** Conda tried to use libmamba solver (faster but incompatible)
- **After:** Conda uses classic solver (slower but stable)

The classic solver is more reliable and compatible. You can switch back to libmamba later once the compatibility issue is resolved in future conda updates.

## Files Modified

- `~/.condarc` - Added `solver: classic` setting
- `~/.condarc.backup` - Backup of original config

## Related Scripts

- `scripts/fix_conda_libmamba.ps1` - Script that applied the fix
- `scripts/diagnose_jupyter.py` - Jupyter diagnostic (unrelated but useful)


