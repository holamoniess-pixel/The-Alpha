"""
ALPHA OMEGA - File Integrity Monitor
Hash Verification & Protected File Monitoring
Version: 2.0.0
"""

import os
import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable, Set
from enum import Enum

logger = logging.getLogger("FileIntegrity")


class IntegrityStatus(Enum):
    VALID = "valid"
    MODIFIED = "modified"
    DELETED = "deleted"
    NEW = "new"
    SUSPICIOUS = "suspicious"


@dataclass
class FileHash:
    path: str
    sha256: str
    md5: str
    size: int
    modified_time: float
    first_seen: float = field(default_factory=time.time)
    last_verified: float = field(default_factory=time.time)
    status: IntegrityStatus = IntegrityStatus.VALID

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "md5": self.md5,
            "size": self.size,
            "modified_time": self.modified_time,
            "first_seen": self.first_seen,
            "last_verified": self.last_verified,
            "status": self.status.value,
        }


@dataclass
class IntegrityReport:
    checked_files: int = 0
    valid_files: int = 0
    modified_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    new_files: List[str] = field(default_factory=list)
    suspicious_files: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "checked_files": self.checked_files,
            "valid_files": self.valid_files,
            "modified_files": self.modified_files,
            "deleted_files": self.deleted_files,
            "new_files": self.new_files,
            "suspicious_files": self.suspicious_files,
            "timestamp": self.timestamp,
        }


class FileIntegrityMonitor:
    DEFAULT_PROTECTED_PATHS = [
        "C:/Windows/System32",
        "C:/Windows/SysWOW64",
        "C:/Program Files",
        "C:/Program Files (x86)",
    ]

    CRITICAL_EXTENSIONS = [
        ".exe",
        ".dll",
        ".sys",
        ".drv",
        ".bat",
        ".cmd",
        ".ps1",
        ".vbs",
        ".msi",
        ".reg",
    ]

    def __init__(self, db_path: str = None, config: dict = None):
        self.config = config or {}
        self.db_path = Path(db_path or "C:/AlphaOmega/data/integrity_db.json")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._hashes: Dict[str, FileHash] = {}
        self._protected_paths: List[str] = []
        self._watching = False
        self._watch_threads: List[threading.Thread] = []
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()

        self._load_database()
        self._init_protected_paths()

    def _init_protected_paths(self):
        custom_paths = self.config.get("protected_paths", [])
        self._protected_paths = self.DEFAULT_PROTECTED_PATHS + custom_paths

        if os.name == "nt":
            username = os.environ.get("USERNAME", "")
            user_paths = [
                f"C:/Users/{username}/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup",
                f"C:/Users/{username}/ntuser.dat",
            ]
            self._protected_paths.extend(user_paths)

    def _load_database(self):
        try:
            if self.db_path.exists():
                data = json.loads(self.db_path.read_text())
                for item in data.get("hashes", []):
                    fh = FileHash(**item)
                    self._hashes[fh.path] = fh
                logger.info(f"Loaded {len(self._hashes)} file hashes from database")
        except Exception as e:
            logger.error(f"Failed to load integrity database: {e}")

    def _save_database(self):
        try:
            data = {
                "hashes": [fh.to_dict() for fh in self._hashes.values()],
                "last_saved": time.time(),
            }
            self.db_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save integrity database: {e}")

    def compute_hash(self, file_path: str | Path) -> tuple:
        path = Path(file_path)
        if not path.exists():
            return "", ""

        sha256 = hashlib.sha256()
        md5 = hashlib.md5()

        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
                    md5.update(chunk)
            return sha256.hexdigest(), md5.hexdigest()
        except Exception as e:
            logger.error(f"Hash computation failed for {path}: {e}")
            return "", ""

    def get_file_info(self, file_path: str | Path) -> Optional[FileHash]:
        path = str(Path(file_path).absolute())
        p = Path(path)

        if not p.exists():
            return None

        sha256, md5 = self.compute_hash(path)
        if not sha256:
            return None

        stat = p.stat()

        return FileHash(
            path=path,
            sha256=sha256,
            md5=md5,
            size=stat.st_size,
            modified_time=stat.st_mtime,
        )

    def verify_file(self, file_path: str, expected_hash: str = None) -> IntegrityStatus:
        path = str(Path(file_path).absolute())

        with self._lock:
            if expected_hash:
                sha256, _ = self.compute_hash(path)
                if sha256 != expected_hash:
                    return IntegrityStatus.MODIFIED
                return IntegrityStatus.VALID

            if path not in self._hashes:
                return IntegrityStatus.NEW

            stored = self._hashes[path]
            current = self.get_file_info(path)

            if current is None:
                return IntegrityStatus.DELETED

            if current.sha256 != stored.sha256:
                return IntegrityStatus.MODIFIED

            if (
                current.size != stored.size
                or current.modified_time != stored.modified_time
            ):
                sha256, _ = self.compute_hash(path)
                if sha256 != stored.sha256:
                    return IntegrityStatus.MODIFIED

            return IntegrityStatus.VALID

    def add_protected_file(self, file_path: str) -> bool:
        path = str(Path(file_path).absolute())

        with self._lock:
            if path in self._hashes:
                return True

            fh = self.get_file_info(path)
            if fh:
                self._hashes[path] = fh
                self._save_database()
                logger.info(f"Added protected file: {path}")
                return True

        return False

    def remove_protected_file(self, file_path: str) -> bool:
        path = str(Path(file_path).absolute())

        with self._lock:
            if path in self._hashes:
                del self._hashes[path]
                self._save_database()
                logger.info(f"Removed protected file: {path}")
                return True

        return False

    def get_protected_files(self) -> List[str]:
        return list(self._hashes.keys())

    def check_system_integrity(self, paths: List[str] = None) -> IntegrityReport:
        report = IntegrityReport()
        check_paths = paths or self._protected_paths

        for check_path in check_paths:
            p = Path(check_path)
            if not p.exists():
                continue

            if p.is_file():
                self._check_single_file(str(p), report)
            elif p.is_dir():
                for ext in self.CRITICAL_EXTENSIONS:
                    for f in p.rglob(f"*{ext}"):
                        self._check_single_file(str(f), report)

        self._save_database()

        if report.modified_files or report.suspicious_files:
            self._notify_change(report)

        return report

    def _check_single_file(self, file_path: str, report: IntegrityReport):
        report.checked_files += 1
        status = self.verify_file(file_path)

        if status == IntegrityStatus.VALID:
            report.valid_files += 1
            with self._lock:
                if file_path in self._hashes:
                    self._hashes[file_path].last_verified = time.time()

        elif status == IntegrityStatus.MODIFIED:
            report.modified_files.append(file_path)
            logger.warning(f"File modified: {file_path}")

        elif status == IntegrityStatus.DELETED:
            report.deleted_files.append(file_path)
            logger.warning(f"File deleted: {file_path}")

        elif status == IntegrityStatus.NEW:
            report.new_files.append(file_path)
            if self._is_suspicious_location(file_path):
                report.suspicious_files.append(file_path)
                logger.warning(f"Suspicious new file: {file_path}")
            else:
                self.add_protected_file(file_path)

    def _is_suspicious_location(self, file_path: str) -> bool:
        path = Path(file_path)
        suspicious_dirs = ["temp", "tmp", "cache", "downloads"]

        for part in path.parts:
            if part.lower() in suspicious_dirs:
                return True

        if os.name == "nt":
            startup = "Startup"
            if startup in path.parts:
                return True

        return False

    def watch_directory(self, directory: str, callback: Callable = None) -> bool:
        if callback:
            self._callbacks.append(callback)

        watch_dir = Path(directory)
        if not watch_dir.exists():
            return False

        def watch_loop():
            known_state = {}
            for f in watch_dir.rglob("*"):
                if f.is_file() and f.suffix.lower() in self.CRITICAL_EXTENSIONS:
                    sha256, _ = self.compute_hash(f)
                    known_state[str(f)] = sha256

            while self._watching:
                try:
                    current_state = {}
                    for f in watch_dir.rglob("*"):
                        if f.is_file() and f.suffix.lower() in self.CRITICAL_EXTENSIONS:
                            sha256, _ = self.compute_hash(f)
                            current_state[str(f)] = sha256

                    for path, hash_val in current_state.items():
                        if path not in known_state:
                            self._on_file_event(path, "created", hash_val)
                        elif known_state[path] != hash_val:
                            self._on_file_event(path, "modified", hash_val)

                    for path in known_state:
                        if path not in current_state:
                            self._on_file_event(path, "deleted", None)

                    known_state = current_state
                except Exception as e:
                    logger.error(f"Watch error: {e}")

                time.sleep(10)

        self._watching = True
        thread = threading.Thread(target=watch_loop, daemon=True)
        thread.start()
        self._watch_threads.append(thread)

        return True

    def _on_file_event(self, path: str, event: str, hash_val: str):
        logger.info(f"File {event}: {path}")
        report = IntegrityReport()

        if event == "created":
            report.new_files.append(path)
            if self._is_suspicious_location(path):
                report.suspicious_files.append(path)
        elif event == "modified":
            report.modified_files.append(path)
        elif event == "deleted":
            report.deleted_files.append(path)

        self._notify_change(report)

    def stop_watching(self):
        self._watching = False
        for thread in self._watch_threads:
            thread.join(timeout=5)
        self._watch_threads.clear()

    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def _notify_change(self, report: IntegrityReport):
        for callback in self._callbacks:
            try:
                callback(report)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def export_hashes(self, output_path: str) -> bool:
        try:
            output = Path(output_path)
            data = {
                "export_time": time.time(),
                "files": [fh.to_dict() for fh in self._hashes.values()],
            }
            output.write_text(json.dumps(data, indent=2))
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def import_hashes(self, input_path: str, merge: bool = True) -> int:
        try:
            data = json.loads(Path(input_path).read_text())
            count = 0

            for item in data.get("files", []):
                fh = FileHash(**item)
                if merge or fh.path not in self._hashes:
                    self._hashes[fh.path] = fh
                    count += 1

            self._save_database()
            return count
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return 0
