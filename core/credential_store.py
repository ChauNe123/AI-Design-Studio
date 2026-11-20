"""Secure Credential Store using Windows Credential Manager (advapi32.dll via ctypes).
Never writes API keys to source code, logs, git, DesignDocument, or project exports.
"""
import ctypes
from ctypes import wintypes
from typing import Optional

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
CRED_TARGET_PREFIX = "AIDesignStudio/"


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


PCREDENTIALW = ctypes.POINTER(CREDENTIALW)

_advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
_CredWriteW = _advapi32.CredWriteW
_CredWriteW.argtypes = [PCREDENTIALW, wintypes.DWORD]
_CredWriteW.restype = wintypes.BOOL

_CredReadW = _advapi32.CredReadW
_CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(PCREDENTIALW)]
_CredReadW.restype = wintypes.BOOL

_CredDeleteW = _advapi32.CredDeleteW
_CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
_CredDeleteW.restype = wintypes.BOOL

_CredFree = _advapi32.CredFree
_CredFree.argtypes = [ctypes.c_void_p]
_CredFree.restype = None


def _target_name(provider_id: str) -> str:
    return f"{CRED_TARGET_PREFIX}{provider_id}"


def save_api_key(provider_id: str, secret_key: str) -> bool:
    if not secret_key:
        raise ValueError("Secret API key cannot be empty.")
    blob_bytes = secret_key.encode("utf-16-le")
    blob_arr = (ctypes.c_ubyte * len(blob_bytes)).from_buffer_copy(blob_bytes)
    cred = CREDENTIALW()
    cred.Flags = 0
    cred.Type = CRED_TYPE_GENERIC
    cred.TargetName = _target_name(provider_id)
    cred.Comment = "AI Design Studio Cloud Provider Credential"
    cred.CredentialBlobSize = len(blob_bytes)
    cred.CredentialBlob = ctypes.cast(blob_arr, ctypes.POINTER(ctypes.c_ubyte))
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE
    cred.UserName = provider_id
    ok = bool(_CredWriteW(ctypes.byref(cred), 0))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return True


def read_api_key(provider_id: str) -> Optional[str]:
    pcred = PCREDENTIALW()
    ok = _CredReadW(_target_name(provider_id), CRED_TYPE_GENERIC, 0, ctypes.byref(pcred))
    if not ok:
        return None
    try:
        size = pcred.contents.CredentialBlobSize
        if size == 0:
            return None
        raw = bytes(ctypes.cast(pcred.contents.CredentialBlob, ctypes.POINTER(ctypes.c_ubyte * size)).contents)
        return raw.decode("utf-16-le", errors="replace")
    finally:
        _CredFree(pcred)


def has_api_key(provider_id: str) -> bool:
    return bool(read_api_key(provider_id))


def delete_api_key(provider_id: str) -> bool:
    return bool(_CredDeleteW(_target_name(provider_id), CRED_TYPE_GENERIC, 0))


def mask_key_hint(secret: Optional[str]) -> str:
    if not secret:
        return "Not configured"
    if len(secret) <= 8:
        return "Configured (****)"
    return f"Configured ({secret[:3]}...{secret[-4:]})"
