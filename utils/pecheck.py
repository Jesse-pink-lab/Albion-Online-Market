import os
import struct

def is_valid_win64_exe(path: str) -> tuple[bool, str]:
    """Check whether ``path`` points to a valid 64-bit Windows executable.

    Returns ``(True, "ok")`` when the file exists and contains a DOS header,
    PE signature and the machine field ``0x8664``.  On failure ``False`` is
    returned along with the specific reason.
    """
    if not os.path.isfile(path):
        return False, "file does not exist"

    try:
        with open(path, "rb") as f:
            if f.read(2) != b"MZ":
                return False, "not MZ"
            f.seek(0x3C)
            e_lfanew_data = f.read(4)
            if len(e_lfanew_data) != 4:
                return False, "no e_lfanew"
            e_lfanew = struct.unpack("<I", e_lfanew_data)[0]
            f.seek(e_lfanew)
            if f.read(4) != b"PE\0\0":
                return False, "no PE signature"
            machine_data = f.read(2)
            if len(machine_data) != 2:
                return False, "no machine"
            machine = struct.unpack("<H", machine_data)[0]
            if machine != 0x8664:
                return False, f"wrong machine 0x{machine:04X}"
        return True, "ok"
    except Exception as exc:  # pragma: no cover - rare I/O issues
        return False, str(exc)
