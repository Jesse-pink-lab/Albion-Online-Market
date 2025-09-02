#!/usr/bin/env python3
"""
Build script for Albion Trade Optimizer.

Creates a standalone executable using PyInstaller.
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

# Build configuration
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")
SPEC_FILE = f"{PROJECT_NAME}.spec"

def clean_build():
    """Clean previous build artifacts."""
    print("🧹 Cleaning previous build artifacts...")
    
    # Remove build directories
    for dir_name in [BUILD_DIR, DIST_DIR, Path("__pycache__")]:
        if dir_name.exists():
            shutil.rmtree(dir_name)
            print(f"  ✓ Removed {dir_name}")
    
    # Remove spec file
    if Path(SPEC_FILE).exists():
        Path(SPEC_FILE).unlink()
        print(f"  ✓ Removed {SPEC_FILE}")
    
    # Remove .pyc files
    for pyc_file in Path(".").rglob("*.pyc"):
        pyc_file.unlink()
    
    print("✅ Build cleanup complete")

def create_spec_file():
    """Create PyInstaller spec file with custom configuration."""
    print("📝 Creating PyInstaller spec file...")
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Add project root to path
project_root = Path.cwd()
sys.path.insert(0, str(project_root))

a = Analysis(
    ['{MAIN_SCRIPT}'],
    pathex=[str(project_root)],
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
        'sqlalchemy.pool',
        'yaml',
        'requests',
        'pandas',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'pytest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

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
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='icon.ico' if Path('icon.ico').exists() else None,
)
'''
    
    with open(SPEC_FILE, 'w') as f:
        f.write(spec_content)
    
    print(f"✅ Created {SPEC_FILE}")

def create_version_info():
    """Create version info file for Windows executable."""
    print("📋 Creating version info file...")
    
    version_info = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Manus AI'),
        StringStruct(u'FileDescription', u'Albion Trade Optimizer - Trade analysis tool for Albion Online'),
        StringStruct(u'FileVersion', u'{VERSION}'),
        StringStruct(u'InternalName', u'{PROJECT_NAME}'),
        StringStruct(u'LegalCopyright', u'Copyright © 2025 Manus AI'),
        StringStruct(u'OriginalFilename', u'{PROJECT_NAME}.exe'),
        StringStruct(u'ProductName', u'Albion Trade Optimizer'),
        StringStruct(u'ProductVersion', u'{VERSION}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    
    with open('version_info.txt', 'w') as f:
        f.write(version_info)
    
    print("✅ Created version_info.txt")

def create_icon():
    """Create a simple icon file if none exists."""
    if not Path('icon.ico').exists():
        print("🎨 Creating default icon...")
        # For now, we'll skip icon creation as it requires additional libraries
        # In a real scenario, you would create or provide an .ico file
        print("  ⚠️ No icon.ico found - executable will use default icon")
    else:
        print("✅ Using existing icon.ico")

def run_pyinstaller():
    """Run PyInstaller to build the executable."""
    print("🔨 Building executable with PyInstaller...")
    
    try:
        # Run PyInstaller with the spec file
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", SPEC_FILE]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ PyInstaller build completed successfully")
        
        # Show build output
        if result.stdout:
            print("Build output:")
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller build failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def verify_build():
    """Verify the build was successful."""
    print("🔍 Verifying build...")
    
    exe_path = DIST_DIR / f"{PROJECT_NAME}.exe"
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ Executable created: {exe_path}")
        print(f"  📏 Size: {size_mb:.1f} MB")
        
        # Test if executable can be run (basic check)
        try:
            # Just check if the file is executable, don't actually run it
            # as it might require GUI environment
            if os.access(exe_path, os.X_OK):
                print("  ✅ Executable has proper permissions")
            else:
                print("  ⚠️ Executable may not have proper permissions")
        except Exception as e:
            print(f"  ⚠️ Could not verify executable: {e}")
        
        return True
    else:
        print(f"❌ Executable not found at {exe_path}")
        return False

def create_installer_script():
    """Create an Inno Setup installer script."""
    print("📦 Creating installer script...")
    
    installer_script = f'''[Setup]
AppName=Albion Trade Optimizer
AppVersion={VERSION}
AppPublisher=Manus AI
AppPublisherURL=https://manus.im
AppSupportURL=https://help.manus.im
AppUpdatesURL=https://manus.im
DefaultDirName={{autopf}}\\AlbionTradeOptimizer
DefaultGroupName=Albion Trade Optimizer
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer
OutputBaseFilename=AlbionTradeOptimizer-{VERSION}-Setup
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "dist\\{PROJECT_NAME}.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{{app}}"; Flags: ignoreversion isreadme

[Icons]
Name: "{{group}}\\Albion Trade Optimizer"; Filename: "{{app}}\\{PROJECT_NAME}.exe"
Name: "{{group}}\\{{cm:UninstallProgram,Albion Trade Optimizer}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\Albion Trade Optimizer"; Filename: "{{app}}\\{PROJECT_NAME}.exe"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{PROJECT_NAME}.exe"; Description: "{{cm:LaunchProgram,Albion Trade Optimizer}}"; Flags: nowait postinstall skipifsilent
'''
    
    with open('installer.iss', 'w') as f:
        f.write(installer_script)
    
    print("✅ Created installer.iss")
    print("  📝 To build installer, install Inno Setup and compile installer.iss")

def create_license():
    """Create a simple license file."""
    if not Path('LICENSE.txt').exists():
        print("📄 Creating license file...")
        
        license_text = f'''Albion Trade Optimizer v{VERSION}
Copyright © 2025 Manus AI

This software is provided "as is" without warranty of any kind.

Permission is hereby granted to use this software for personal, 
non-commercial purposes related to Albion Online gameplay.

This software is not affiliated with or endorsed by Sandbox Interactive GmbH.
Albion Online is a trademark of Sandbox Interactive GmbH.

For support and updates, visit: https://help.manus.im
'''
        
        with open('LICENSE.txt', 'w') as f:
            f.write(license_text)
        
        print("✅ Created LICENSE.txt")

def create_readme():
    """Create a README file for the distribution."""
    if not Path('README.md').exists():
        print("📖 Creating README file...")
        
        readme_text = f'''# Albion Trade Optimizer v{VERSION}

A powerful desktop application for Albion Online players to identify profitable trade opportunities and optimize crafting decisions.

## Features

- **Flip Finder**: Discover profitable trade routes between cities
- **Crafting Optimizer**: Calculate optimal crafting strategies
- **Real-time Data**: Uses live market data from Albion Online Data Project
- **Risk Assessment**: Automatic risk classification for trade routes
- **User-friendly GUI**: Modern desktop interface built with PySide6

## Getting Started

1. Launch the application
2. Configure your settings (premium status, preferred cities, etc.)
3. Use the Flip Finder to discover trade opportunities
4. Analyze crafting profitability with the Crafting Optimizer
5. Monitor market data with the Data Manager

## System Requirements

- Windows 10 or later (64-bit)
- Internet connection for market data
- Minimum 4GB RAM
- 100MB free disk space

## Support

For help and support, visit: https://help.manus.im

## Disclaimer

This software is not affiliated with or endorsed by Sandbox Interactive GmbH.
Albion Online is a trademark of Sandbox Interactive GmbH.

Use this tool responsibly and in accordance with Albion Online's Terms of Service.
'''
        
        with open('README.md', 'w') as f:
            f.write(readme_text)
        
        print("✅ Created README.md")

def main():
    """Main build process."""
    print(f"🚀 Building {PROJECT_NAME} v{VERSION}")
    print("=" * 50)
    
    # Check if main script exists
    if not Path(MAIN_SCRIPT).exists():
        print(f"❌ Main script {MAIN_SCRIPT} not found!")
        return False
    
    try:
        # Build steps
        clean_build()
        create_version_info()
        create_icon()
        create_license()
        create_readme()
        create_spec_file()
        
        # Run PyInstaller
        if not run_pyinstaller():
            return False
        
        # Verify build
        if not verify_build():
            return False
        
        # Create installer script
        create_installer_script()
        
        print("=" * 50)
        print("🎉 Build completed successfully!")
        print(f"📁 Executable: dist/{PROJECT_NAME}.exe")
        print(f"📦 Installer script: installer.iss")
        print()
        print("Next steps:")
        print("1. Test the executable on a clean Windows system")
        print("2. Install Inno Setup to build the installer")
        print("3. Compile installer.iss to create setup.exe")
        
        return True
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

