import os
import sys
import time
import ctypes
from ctypes import wintypes
import json
from pathlib import Path

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2

class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]

PCREDENTIAL = ctypes.POINTER(CREDENTIAL)
advapi32 = ctypes.windll.advapi32

CredReadW = advapi32.CredReadW
CredReadW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(PCREDENTIAL)]
CredReadW.restype = wintypes.BOOL

CredWriteW = advapi32.CredWriteW
CredWriteW.argtypes = [PCREDENTIAL, wintypes.DWORD]
CredWriteW.restype = wintypes.BOOL

CredFree = advapi32.CredFree
CredFree.argtypes = [ctypes.c_void_p]

CredDeleteW = advapi32.CredDeleteW
CredDeleteW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
CredDeleteW.restype = wintypes.BOOL


def read_credential(target="gemini:antigravity"):
    pcred = PCREDENTIAL()
    if CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
        try:
            cred = pcred.contents
            blob = bytes(cred.CredentialBlob[:cred.CredentialBlobSize])
            username = cred.UserName
            return {"username": username, "blob": blob.decode("utf-8")}
        finally:
            CredFree(pcred)
    return None


def write_credential(target="gemini:antigravity", username="antigravity", blob_str=""):
    blob_bytes = blob_str.encode("utf-8")
    blob_array = (ctypes.c_byte * len(blob_bytes))(*blob_bytes)

    cred = CREDENTIAL()
    cred.Flags = 0
    cred.Type = CRED_TYPE_GENERIC
    cred.TargetName = target
    cred.Comment = None
    cred.CredentialBlobSize = len(blob_bytes)
    cred.CredentialBlob = ctypes.cast(blob_array, ctypes.POINTER(ctypes.c_byte))
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE
    cred.AttributeCount = 0
    cred.Attributes = None
    cred.TargetAlias = None
    cred.UserName = username

    return bool(CredWriteW(ctypes.byref(cred), 0))


def delete_credential(target="gemini:antigravity"):
    return bool(CredDeleteW(target, CRED_TYPE_GENERIC, 0))


def save_to_file(file_path: Path, target="gemini:antigravity") -> bool:
    cred = read_credential(target)
    if not cred:
        return False
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cred, f, indent=2)
    return True


def load_from_file(file_path: Path, target="gemini:antigravity") -> bool:
    file_path = Path(file_path)
    if not file_path.exists():
        return False
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return write_credential(target, username=data.get("username", "antigravity"), blob_str=data.get("blob", ""))


class TemporaryCredentialSwap:
    """
    Context manager that temporarily swaps the Windows Credential with another account's token,
    and reliably restores the original token upon exit.
    Includes cross-process lock protection to prevent race conditions during parallel stress tests.
    """
    def __init__(self, target_cred_file: Path, target="gemini:antigravity"):
        self.target_cred_file = Path(target_cred_file)
        self.target = target
        self.original_cred = None
        self.lock_file = self.target_cred_file.parent / "wincred.lock"

    def _acquire_lock(self, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            try:
                # O_CREAT | O_EXCL is atomic across processes
                self.fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                return True
            except FileExistsError:
                # If lock is stale (>60s), remove it
                try:
                    if self.lock_file.exists() and (time.time() - self.lock_file.stat().st_mtime > 60):
                        self.lock_file.unlink(missing_ok=True)
                except Exception:
                    pass
                time.sleep(0.2)
        return False

    def _release_lock(self):
        try:
            if hasattr(self, "fd"):
                os.close(self.fd)
            self.lock_file.unlink(missing_ok=True)
        except Exception:
            pass

    def __enter__(self):
        if not self.target_cred_file.exists():
            raise FileNotFoundError(f"Credential file not found: {self.target_cred_file}")
        
        self._acquire_lock()

        # Backup currently active credential
        self.original_cred = read_credential(self.target)
        
        # Read secondary credential and apply
        with open(self.target_cred_file, "r", encoding="utf-8") as f:
            secondary_data = json.load(f)
        
        write_credential(
            self.target,
            username=secondary_data.get("username", "antigravity"),
            blob_str=secondary_data.get("blob", "")
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # Restore original credential
            if self.original_cred:
                write_credential(
                    self.target,
                    username=self.original_cred.get("username", "antigravity"),
                    blob_str=self.original_cred.get("blob", "")
                )
        finally:
            self._release_lock()


if __name__ == "__main__":
    current = read_credential()
    if current:
        backup_path = Path(".agents/credentials/conta1.json")
        save_to_file(backup_path)
        print("Conta 1 salva com sucesso em:", backup_path)
    else:
        print("Nenhuma credencial encontrada no Windows Credential Manager.")
