import os
import struct
import subprocess


def detect_arch(path: str) -> str:
    """Detect the architecture of a PE file.

    Returns:
        '32-bit' if x86,
        '64-bit' if x64,
        'not-pe' if not a valid PE file,
        'missing' if the file can't be read,
        otherwise a string describing the issue.
    """
    try:
        with open(path, 'rb') as f:
            if f.read(2) != b'MZ':
                return 'not-pe'
            f.seek(0x3C)
            e_lfanew = struct.unpack('<I', f.read(4))[0]
            f.seek(e_lfanew)
            if f.read(4) != b'PE\0\0':
                return 'not-pe'
            machine = struct.unpack('<H', f.read(2))[0]
            if machine == 0x14C:
                return '32-bit'
            if machine == 0x8664:
                return '64-bit'
            return f'unknown (machine=0x{machine:X})'
    except OSError:
        return 'missing'


def main() -> None:
    exe_path = os.path.join(os.path.dirname(__file__), 'bin', 'albiondata-client.exe')
    arch = detect_arch(exe_path)
    if arch != '64-bit':
        print('This albiondata-client.exe is not Windows 64-bit — download the official Windows build instead.')
        print(f'Detected architecture: {arch}')
        return

    try:
        proc = subprocess.Popen([exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stdout:
            print(stdout.decode('utf-8', errors='ignore'))
        if stderr:
            print(stderr.decode('utf-8', errors='ignore'))
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 216:
            print('Failed to launch albiondata-client.exe: this version is not compatible with your Windows.')
        else:
            print(f'Failed to launch albiondata-client.exe: {exc}')


if __name__ == '__main__':
    main()
