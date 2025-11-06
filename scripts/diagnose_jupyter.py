#!/usr/bin/env python3
"""
Diagnostic script for Jupyter notebook issues.
Checks kernel configuration, dependencies, and provides fixes.
"""

import sys
import json
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def run_command(cmd: List[str], env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def check_python_version() -> Tuple[bool, str]:
    """Check Python version."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print(f"[OK] Current Python version: {version_str}")
    return True, version_str

def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if required dependencies are installed."""
    required = [
        'numpy', 'pandas', 'scipy', 'matplotlib', 'seaborn',
        'jupyter', 'notebook', 'ipykernel'
    ]
    optional = ['hrvanalysis']
    
    missing = []
    available = []
    
    for pkg in required:
        try:
            __import__(pkg)
            available.append(pkg)
            print(f"[OK] {pkg} installed")
        except ImportError:
            missing.append(pkg)
            print(f"[MISSING] {pkg} MISSING")
    
    for pkg in optional:
        try:
            __import__(pkg)
            available.append(pkg)
            print(f"[OK] {pkg} installed (optional)")
        except ImportError:
            print(f"[WARN] {pkg} not installed (optional)")
    
    return len(missing) == 0, missing

def check_kernel_config() -> Tuple[bool, Dict]:
    """Check Jupyter kernel configuration."""
    kernel_path = Path.home() / "AppData" / "Roaming" / "jupyter" / "kernels" / "valquiria-analysis"
    kernel_json = kernel_path / "kernel.json"
    
    if not kernel_json.exists():
        print(f"[ERROR] Kernel configuration not found at {kernel_json}")
        return False, {}
    
    try:
        with open(kernel_json, 'r') as f:
            config = json.load(f)
        
        python_exe = config.get('argv', [None])[0]
        if python_exe and Path(python_exe).exists():
            print(f"[OK] Kernel Python: {python_exe}")
            # Check Python version in kernel
            exit_code, stdout, stderr = run_command([python_exe, '--version'])
            if exit_code == 0:
                print(f"  Version: {stdout.strip()}")
        else:
            print(f"[ERROR] Kernel Python executable not found: {python_exe}")
            return False, config
        
        return True, config
    except Exception as e:
        print(f"[ERROR] Error reading kernel config: {e}")
        return False, {}

def check_notebook_metadata(notebook_path: Path) -> Tuple[bool, Dict]:
    """Check notebook metadata for kernel configuration."""
    if not notebook_path.exists():
        print(f"[ERROR] Notebook not found: {notebook_path}")
        return False, {}
    
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        metadata = nb.get('metadata', {})
        kernelspec = metadata.get('kernelspec', {})
        language_info = metadata.get('language_info', {})
        
        kernel_name = kernelspec.get('name', 'unknown')
        display_name = kernelspec.get('display_name', 'unknown')
        python_version = language_info.get('version', 'unknown')
        
        print(f"[OK] Notebook kernel: {kernel_name} ({display_name})")
        print(f"  Python version in metadata: {python_version}")
        
        return True, {
            'kernelspec': kernelspec,
            'language_info': language_info
        }
    except Exception as e:
        print(f"[ERROR] Error reading notebook: {e}")
        return False, {}

def test_kernel_start() -> bool:
    """Test if kernel can start."""
    print("\nTesting kernel startup...")
    try:
        # Try to import ipykernel
        import ipykernel
        print("[OK] ipykernel can be imported")
        
        # Check if kernel can be found
        exit_code, stdout, stderr = run_command([
            sys.executable, '-m', 'jupyter', 'kernelspec', 'list'
        ])
        if exit_code == 0:
            if 'valquiria-analysis' in stdout:
                print("[OK] valquiria-analysis kernel found")
                return True
            else:
                print("[ERROR] valquiria-analysis kernel not found in list")
                return False
        else:
            print(f"[ERROR] Error listing kernels: {stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Error testing kernel: {e}")
        return False

def fix_notebook_metadata(notebook_path: Path, python_version: str) -> bool:
    """Fix notebook metadata to match current Python version."""
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        # Update language_info version
        if 'metadata' not in nb:
            nb['metadata'] = {}
        if 'language_info' not in nb['metadata']:
            nb['metadata']['language_info'] = {}
        
        nb['metadata']['language_info']['version'] = python_version
        
        # Backup original
        backup_path = notebook_path.with_suffix('.ipynb.backup')
        if not backup_path.exists():
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1)
            print(f"[OK] Created backup: {backup_path}")
        
        # Write updated notebook
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        
        print(f"[OK] Updated notebook metadata: Python {python_version}")
        return True
    except Exception as e:
        print(f"[ERROR] Error fixing notebook: {e}")
        return False

def reinstall_kernel() -> bool:
    """Reinstall the Jupyter kernel."""
    print("\nReinstalling kernel...")
    try:
        exit_code, stdout, stderr = run_command([
            sys.executable, '-m', 'ipykernel', 'install',
            '--user', '--name=valquiria-analysis',
            '--display-name=Valquiria Space Analog Analysis'
        ])
        if exit_code == 0:
            print("[OK] Kernel reinstalled successfully")
            return True
        else:
            print(f"[ERROR] Error reinstalling kernel: {stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def main():
    """Main diagnostic function."""
    print("=" * 80)
    print("Jupyter Notebook Diagnostic Tool")
    print("=" * 80)
    print()
    
    # Get script directory
    script_dir = Path(__file__).parent
    notebook_path = script_dir / "HRV_Comprehensive_Analysis.ipynb"
    
    print("1. Checking Python version...")
    success, python_version = check_python_version()
    print()
    
    print("2. Checking dependencies...")
    deps_ok, missing = check_dependencies()
    print()
    
    print("3. Checking kernel configuration...")
    kernel_ok, kernel_config = check_kernel_config()
    print()
    
    print("4. Checking notebook metadata...")
    nb_ok, nb_metadata = check_notebook_metadata(notebook_path)
    print()
    
    print("5. Testing kernel...")
    kernel_test_ok = test_kernel_start()
    print()
    
    # Summary
    print("=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    
    issues = []
    if not deps_ok:
        issues.append(f"Missing dependencies: {', '.join(missing)}")
    if not kernel_ok:
        issues.append("Kernel configuration issue")
    if not kernel_test_ok:
        issues.append("Kernel cannot start")
    
    if issues:
        print("\n[WARN] ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        
        print("\n[INFO] RECOMMENDED FIXES:")
        
        if missing:
            print(f"\n1. Install missing dependencies:")
            print(f"   pip install {' '.join(missing)}")
        
        if not kernel_test_ok:
            print("\n2. Reinstall kernel:")
            print("   python -m ipykernel install --user --name=valquiria-analysis --display-name='Valquiria Space Analog Analysis'")
        
        # Offer to fix automatically
        print("\nWould you like to attempt automatic fixes? (This will modify the notebook)")
        print("Run with --fix flag to apply fixes automatically")
        
    else:
        print("\n[OK] All checks passed! Your Jupyter setup looks good.")
        print("\nIf notebooks still don't run, try:")
        print("  1. Restart Jupyter server")
        print("  2. Select the correct kernel in the notebook (Kernel -> Change Kernel)")
        print("  3. Check Jupyter server logs for errors")
    
    # Apply fixes if requested
    if '--fix' in sys.argv:
        print("\n" + "=" * 80)
        print("APPLYING FIXES")
        print("=" * 80)
        
        if missing:
            print("\nInstalling missing dependencies...")
            exit_code, stdout, stderr = run_command([
                sys.executable, '-m', 'pip', 'install'] + missing
            )
            if exit_code == 0:
                print("[OK] Dependencies installed")
            else:
                print(f"[ERROR] Error: {stderr}")
        
        if not kernel_test_ok:
            reinstall_kernel()
        
        if nb_ok and notebook_path.exists():
            fix_notebook_metadata(notebook_path, python_version)
        
        print("\n[OK] Fixes applied. Please restart Jupyter and try again.")

if __name__ == '__main__':
    main()

