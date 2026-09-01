"""Abstração de storage de mídia. Em dev: disco local em volume Docker.

Guarde sempre a *key* (caminho relativo) no banco; a URL pública é derivada.
"""
from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings


class Storage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def url(self, key: str) -> str: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalStorage(Storage):
    def __init__(self, root: str, base_url: str) -> None:
        self.root = Path(root)
        self.base_url = base_url.rstrip("/")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("key fora do diretório de mídia")
        return p

    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # escrita atômica: grava num temporário no mesmo diretório e renomeia,
        # para nunca deixar um arquivo pela metade se o processo cair no meio.
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".part")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
        return key

    def delete(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass

    def url(self, key: str) -> str:
        return f"{self.base_url}/{key.lstrip('/')}"

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        try:
            return self._path(key).is_file()
        except ValueError:
            return False


def get_storage() -> Storage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.storage_local_dir, settings.media_base_url)
    raise NotImplementedError(f"storage backend '{settings.storage_backend}' não implementado")


storage = get_storage()
