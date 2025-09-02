# Albion Trade Optimizer - Deployment Guide

This guide covers the complete process for packaging and distributing the Albion Trade Optimizer as a Windows desktop application.

## Overview

The deployment process involves:
1. Building a standalone executable using PyInstaller
2. Creating a Windows installer using Inno Setup
3. Code signing (optional but recommended)
4. Distribution and updates

## Build Environment Setup

### Windows Development Machine

**Required Software:**
- Windows 10/11 (64-bit)
- Python 3.11+ (from python.org)
- Git (optional)
- Inno Setup 6.x
- Code signing certificate (optional)

**Environment Setup:**
```cmd
# Clone the repository
git clone <repository-url>
cd AlbionTradeOptimizer

# Run the automated build script
build_windows.bat
```

### Manual Build Process

If you prefer manual control over the build process:

```cmd
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# 3. Test the application
python main.py

# 4. Build executable
python build.py

# 5. Test executable
dist\AlbionTradeOptimizer.exe
```

## Build Configuration

### PyInstaller Configuration

The build process uses a custom PyInstaller spec file with optimizations:

- **One-file bundle**: All dependencies packaged into a single .exe
- **Windows subsystem**: No console window (GUI only)
- **UPX compression**: Reduces file size
- **Version info**: Embedded version and company information
- **Icon**: Custom application icon (if provided)

### Included Files

The executable automatically includes:
- All Python dependencies
- Configuration files (config.yaml)
- Recipe data (recipes.json, items.txt)
- SQLite database engine
- PySide6 GUI framework

### Excluded Files

To reduce size, the following are excluded:
- Development tools (pytest, sphinx)
- Unused GUI frameworks (tkinter)
- Large optional libraries (matplotlib, PIL)

## Installer Creation

### Inno Setup Configuration

The build process generates `installer.iss` with:

- **Modern wizard style**: Professional installation experience
- **Minimal privileges**: Installs to user directory by default
- **Desktop shortcut**: Optional desktop icon
- **Uninstaller**: Automatic uninstall support
- **File associations**: (Future enhancement)

### Building the Installer

```cmd
# Option 1: Using Inno Setup GUI
1. Open Inno Setup Compiler
2. Open installer.iss
3. Click Build > Compile

# Option 2: Command line
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## Code Signing (Recommended)

For professional distribution, sign both the executable and installer:

### Obtaining a Certificate

1. Purchase from a trusted CA (DigiCert, Sectigo, etc.)
2. Use EV (Extended Validation) certificate for immediate trust
3. Store certificate securely

### Signing Process

```cmd
# Sign the executable
signtool sign /f certificate.p12 /p password /t http://timestamp.digicert.com dist\AlbionTradeOptimizer.exe

# Sign the installer
signtool sign /f certificate.p12 /p password /t http://timestamp.digicert.com installer\AlbionTradeOptimizer-Setup.exe
```

### Automated Signing

Update `build.py` to include signing:

```python
def sign_executable(exe_path, cert_path, cert_password):
    """Sign executable with code signing certificate."""
    cmd = [
        "signtool", "sign",
        "/f", cert_path,
        "/p", cert_password,
        "/t", "http://timestamp.digicert.com",
        "/fd", "SHA256",
        str(exe_path)
    ]
    subprocess.run(cmd, check=True)
```

## Distribution Strategies

### Direct Distribution

**Pros:**
- Simple and immediate
- No installation required
- Portable application

**Cons:**
- Larger download size
- No automatic updates
- Manual file management

**Method:**
- Distribute `AlbionTradeOptimizer.exe` directly
- Include README.txt with instructions
- Package in ZIP file with documentation

### Installer Distribution

**Pros:**
- Professional installation experience
- Automatic shortcuts and file associations
- Uninstall support
- Smaller download (compressed)

**Cons:**
- Requires installation process
- May trigger antivirus warnings

**Method:**
- Distribute `AlbionTradeOptimizer-Setup.exe`
- Host on website or file sharing service
- Provide installation instructions

### Microsoft Store (Future)

**Pros:**
- Automatic updates
- Trusted distribution channel
- Easy discovery

**Cons:**
- Approval process required
- Store policies and restrictions
- Revenue sharing

**Requirements:**
- MSIX packaging
- Store developer account
- Compliance with store policies

## Update Mechanism

### Manual Updates

Current approach:
1. User downloads new version
2. Uninstalls old version (if using installer)
3. Installs new version

### Automatic Updates (Future Enhancement)

Implement auto-update system:

```python
class UpdateChecker:
    def check_for_updates(self):
        """Check for new version on server."""
        # Compare current version with server version
        # Download and apply updates if available
        pass
```

## Quality Assurance

### Testing Checklist

Before release, test on:

- [ ] Clean Windows 10 system
- [ ] Clean Windows 11 system
- [ ] System without Python installed
- [ ] System with different Python versions
- [ ] Antivirus software enabled
- [ ] Limited user account (non-admin)

### Performance Testing

- [ ] Startup time < 5 seconds
- [ ] Memory usage < 200MB
- [ ] API response handling
- [ ] Database operations
- [ ] GUI responsiveness

### Security Testing

- [ ] No hardcoded credentials
- [ ] Secure API communication (HTTPS)
- [ ] Input validation
- [ ] File system permissions
- [ ] Network security

## Troubleshooting

### Common Build Issues

**PyInstaller fails:**
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Check for missing dependencies
- Disable antivirus temporarily

**Large executable size:**
- Review included dependencies
- Add more exclusions to spec file
- Enable UPX compression

**Runtime errors:**
- Test in clean environment
- Check for missing data files
- Verify all imports are included

### Distribution Issues

**Antivirus false positives:**
- Submit to antivirus vendors for whitelisting
- Use code signing certificate
- Build on clean system

**Installation failures:**
- Test installer on clean systems
- Check Windows compatibility
- Verify installer permissions

## Monitoring and Analytics

### Usage Tracking (Optional)

Implement anonymous usage analytics:

```python
class Analytics:
    def track_startup(self):
        """Track application startup."""
        # Send anonymous usage data
        pass
    
    def track_feature_usage(self, feature):
        """Track feature usage."""
        # Help prioritize development
        pass
```

### Error Reporting

Implement crash reporting:

```python
class ErrorReporter:
    def report_crash(self, exception):
        """Report application crashes."""
        # Send crash reports for debugging
        pass
```

## Legal Considerations

### Licensing

- Include appropriate license file
- Respect third-party library licenses
- Consider open source vs. proprietary licensing

### Privacy

- Clearly state data collection practices
- Implement privacy controls
- Comply with applicable regulations (GDPR, etc.)

### Disclaimers

- Not affiliated with Sandbox Interactive
- Use at your own risk
- Compliance with game terms of service

## Support and Maintenance

### User Support

- Create documentation website
- Set up support email/forum
- Provide troubleshooting guides

### Maintenance Schedule

- Regular dependency updates
- Security patches
- Feature enhancements
- Bug fixes

### Version Management

Use semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes

## Conclusion

This deployment guide provides a comprehensive approach to packaging and distributing the Albion Trade Optimizer. Following these practices ensures a professional, secure, and maintainable distribution process.

For questions or support, contact: support@manus.im

