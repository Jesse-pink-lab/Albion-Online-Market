# Building Albion Trade Optimizer for Windows

This document provides instructions for building the Albion Trade Optimizer as a Windows executable.

## Prerequisites

### System Requirements
- Windows 10 or later (64-bit)
- Python 3.11 or later
- Git (optional, for cloning the repository)

### Required Software
1. **Python 3.11+**: Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation
   - Verify installation: `python --version`

2. **Inno Setup** (for installer creation): Download from [jrsoftware.org](https://jrsoftware.org/isinfo.php)

## Build Process

### Step 1: Prepare the Environment

1. Open Command Prompt or PowerShell as Administrator
2. Clone or extract the project files to a directory (e.g., `C:\AlbionTradeOptimizer`)
3. Navigate to the project directory:
   ```cmd
   cd C:\AlbionTradeOptimizer
   ```

### Step 2: Set Up Python Environment

1. Create a virtual environment:
   ```cmd
   python -m venv venv
   ```

2. Activate the virtual environment:
   ```cmd
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

### Step 3: Test the Application

Before building, test that the application runs correctly:
```cmd
python main.py
```

The GUI should open without errors. Close the application before proceeding.

### Step 4: Build the Executable

Run the build script:
```cmd
python build.py
```

This will:
- Clean previous build artifacts
- Create version info and metadata files
- Generate a PyInstaller spec file
- Build the standalone executable
- Create installer scripts

### Step 5: Verify the Build

1. Check that the executable was created:
   ```cmd
   dir dist\AlbionTradeOptimizer.exe
   ```

2. Test the executable:
   ```cmd
   dist\AlbionTradeOptimizer.exe
   ```

The application should start and function normally.

### Step 6: Create the Installer (Optional)

1. Open Inno Setup Compiler
2. Open the generated `installer.iss` file
3. Click "Build" → "Compile"
4. The installer will be created in the `installer` directory

## Build Outputs

After a successful build, you will have:

- `dist/AlbionTradeOptimizer.exe` - Standalone executable
- `installer.iss` - Inno Setup script
- `installer/AlbionTradeOptimizer-1.0.0-Setup.exe` - Windows installer (if built)

## Troubleshooting

### Common Issues

1. **"Python not found"**
   - Ensure Python is installed and added to PATH
   - Try using `py` instead of `python`

2. **"Module not found" errors**
   - Ensure virtual environment is activated
   - Reinstall dependencies: `pip install -r requirements.txt`

3. **PyInstaller fails**
   - Try updating PyInstaller: `pip install --upgrade pyinstaller`
   - Check for antivirus interference
   - Run as Administrator

4. **Executable doesn't start**
   - Check Windows Defender/antivirus settings
   - Try running from command line to see error messages
   - Ensure all dependencies are included in the spec file

### Build Configuration

The build process can be customized by editing `build.py`:

- **Icon**: Place `icon.ico` in the project root
- **Version**: Update the `VERSION` variable
- **Dependencies**: Modify the `hiddenimports` list in the spec file
- **Data files**: Add additional files to the `datas` list

### Performance Optimization

For smaller executable size:
1. Remove unused dependencies from `requirements.txt`
2. Add more modules to the `excludes` list in the spec file
3. Use UPX compression (enabled by default)

### Code Signing (Optional)

For distribution, consider code signing the executable:
1. Obtain a code signing certificate
2. Use `signtool.exe` to sign the executable
3. Update the Inno Setup script to sign the installer

## Distribution

The final executable can be distributed in several ways:

1. **Standalone executable**: Share `AlbionTradeOptimizer.exe` directly
2. **ZIP archive**: Package the executable with documentation
3. **Windows installer**: Use the generated setup.exe for professional distribution

## Notes

- The executable is platform-specific (Windows only)
- First startup may be slower due to extraction of bundled files
- The executable includes all dependencies and doesn't require Python installation
- Total size is typically 50-100MB depending on dependencies

For support or issues, visit: https://help.manus.im

