#!/usr/bin/env python3
"""
Linux build script for Albion Trade Optimizer.

Creates a Linux executable for demonstration purposes.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Project configuration
PROJECT_NAME = "AlbionTradeOptimizer"
MAIN_SCRIPT = "main.py"
VERSION = "1.0.0"

def create_simple_spec():
    """Create a simple PyInstaller spec file for Linux."""
    print("📝 Creating Linux PyInstaller spec file...")
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{MAIN_SCRIPT}'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
        ('recipes/recipes.json', 'recipes/'),
        ('recipes/items.txt', 'recipes/'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets', 
        'PySide6.QtGui',
        'sqlalchemy.dialects.sqlite',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='{PROJECT_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
'''
    
    with open(f'{PROJECT_NAME}_linux.spec', 'w') as f:
        f.write(spec_content)
    
    print(f"✅ Created {PROJECT_NAME}_linux.spec")

def build_linux():
    """Build Linux executable."""
    print("🔨 Building Linux executable...")
    
    try:
        # Clean previous builds
        for path in ['build', 'dist']:
            if Path(path).exists():
                shutil.rmtree(path)
        
        # Create spec file
        create_simple_spec()
        
        # Run PyInstaller
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", f"{PROJECT_NAME}_linux.spec"]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ Linux build completed successfully")
        
        # Check if executable was created
        exe_path = Path("dist") / PROJECT_NAME
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📁 Executable created: {exe_path}")
            print(f"📏 Size: {size_mb:.1f} MB")
            
            # Make executable
            os.chmod(exe_path, 0o755)
            print("✅ Executable permissions set")
            
            return True
        else:
            print("❌ Executable not found")
            return False
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        if e.stderr:
            print("Error output:", e.stderr)
        return False

def main():
    """Main build process."""
    print(f"🐧 Building {PROJECT_NAME} v{VERSION} for Linux")
    print("=" * 50)
    
    # Check if main script exists
    if not Path(MAIN_SCRIPT).exists():
        print(f"❌ Main script {MAIN_SCRIPT} not found!")
        return False
    
    success = build_linux()
    
    if success:
        print("=" * 50)
        print("🎉 Linux build completed successfully!")
        print(f"📁 Executable: dist/{PROJECT_NAME}")
        print()
        print("Note: This Linux executable is for demonstration purposes.")
        print("For Windows distribution, use the Windows build process.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

