import fsspec
from fsspec.utils import get_protocol
from fsspec.spec import AbstractBufferedFile
from io import TextIOWrapper
from typing import Any

def read_file(file_path: str, **kwargs) -> TextIOWrapper | AbstractBufferedFile:
    protocol: str = get_protocol(url=file_path)
    fs: fsspec.AbstractFileSystem = fsspec.filesystem(
        protocol=protocol,
        storage_options=kwargs)
    return fs.open(path=file_path, mode="r", encoding="utf-8")
    
def read_bytes(file_path: str, **kwargs) -> str | bytes:
    protocol: str = get_protocol(url=file_path)
    fs: fsspec.AbstractFileSystem = fsspec.filesystem(
        protocol=protocol,
        storage_options=kwargs)
    return fs.read_bytes(path=file_path)
