"""Save a model key with Windows DPAPI, never as plaintext or a CLI argument."""
import ctypes
import getpass
import json
import os
from pathlib import Path
import sys


def save(settings):
    if os.name != 'nt':
        raise RuntimeError('Use backend secret environment variables on non-Windows hosts')
    if settings.get('provider') != 'deepseek' or not settings.get('key', '').strip():
        raise ValueError('A DeepSeek key is required')
    class Blob(ctypes.Structure):
        _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    raw = json.dumps(settings).encode('utf-8')
    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    source, output = Blob(len(raw), buffer), Blob()
    protect = ctypes.windll.crypt32.CryptProtectData
    protect.argtypes = [ctypes.POINTER(Blob), ctypes.c_wchar_p, ctypes.c_void_p,
                        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    protect.restype = ctypes.c_int
    if not protect(ctypes.byref(source), 'Campus backend model', None, None, None, 1, ctypes.byref(output)):
        raise RuntimeError('Windows encryption failed')
    try:
        folder = Path(__file__).resolve().parents[1] / '.local'
        folder.mkdir(exist_ok=True)
        (folder / 'model.dpapi').write_bytes(ctypes.string_at(output.data, output.size))
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(output.data)


if __name__ == '__main__':
    value = json.load(sys.stdin) if '--stdin' in sys.argv else {
        'provider': 'deepseek', 'model': 'deepseek-flash', 'enabled': '1',
        'responsePolicy': 'classified-template', 'key': getpass.getpass('DeepSeek API key: '),
    }
    save(value)
    print('Encrypted backend model settings saved. No secret was printed.')
