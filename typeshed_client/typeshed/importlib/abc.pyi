import sys
import types
from _typeshed import (
    OpenBinaryMode,
    OpenBinaryModeReading,
    OpenBinaryModeUpdating,
    OpenBinaryModeWriting,
    OpenTextMode,
    ReadableBuffer,
)
from abc import ABCMeta, abstractmethod
from collections.abc import Iterator, Mapping, Sequence
from importlib.machinery import ModuleSpec
from io import BufferedRandom, BufferedReader, BufferedWriter, FileIO, TextIOWrapper
from typing import IO, Any, BinaryIO, NoReturn, Protocol, overload, runtime_checkable
from typing_extensions import Literal

if sys.version_info >= (3, 11):
    __all__ = [
        "Loader",
        "Finder",
        "MetaPathFinder",
        "PathEntryFinder",
        "ResourceLoader",
        "InspectLoader",
        "ExecutionLoader",
        "FileLoader",
        "SourceLoader",
        "ResourceReader",
        "Traversable",
        "TraversableResources",
    ]

class Finder(metaclass=ABCMeta): ...

class Loader(metaclass=ABCMeta):
    def load_module(self, fullname: str) -> types.ModuleType: ...
    def module_repr(self, module: types.ModuleType) -> str: ...
    def create_module(self, spec: ModuleSpec) -> types.ModuleType | None: ...
    # Not defined on the actual class for backwards-compatibility reasons,
    # but expected in new code.
    def exec_module(self, module: types.ModuleType) -> None: ...

class ResourceLoader(Loader):
    @abstractmethod
    def get_data(self, path: str) -> bytes: ...

class InspectLoader(Loader):
    def is_package(self, fullname: str) -> bool: ...
    def get_code(self, fullname: str) -> types.CodeType | None: ...
    @abstractmethod
    def get_source(self, fullname: str) -> str | None: ...
    def exec_module(self, module: types.ModuleType) -> None: ...
    @staticmethod
    def source_to_code(data: ReadableBuffer | str, path: str = ...) -> types.CodeType: ...

class ExecutionLoader(InspectLoader):
    @abstractmethod
    def get_filename(self, fullname: str) -> str: ...

class SourceLoader(ResourceLoader, ExecutionLoader, metaclass=ABCMeta):
    def path_mtime(self, path: str) -> float: ...
    def set_data(self, path: str, data: bytes) -> None: ...
    def get_source(self, fullname: str) -> str | None: ...
    def path_stats(self, path: str) -> Mapping[str, Any]: ...

# Please keep in sync with sys._MetaPathFinder
class MetaPathFinder(Finder):
    def find_module(self, fullname: str, path: Sequence[str] | None) -> Loader | None: ...
    def invalidate_caches(self) -> None: ...
    # Not defined on the actual class, but expected to exist.
    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: types.ModuleType | None = ...
    ) -> ModuleSpec | None: ...

class PathEntryFinder(Finder):
    def find_module(self, fullname: str) -> Loader | None: ...
    def find_loader(self, fullname: str) -> tuple[Loader | None, Sequence[str]]: ...
    def invalidate_caches(self) -> None: ...
    # Not defined on the actual class, but expected to exist.
    def find_spec(self, fullname: str, target: types.ModuleType | None = ...) -> ModuleSpec | None: ...

class FileLoader(ResourceLoader, ExecutionLoader, metaclass=ABCMeta):
    name: str
    path: str
    def __init__(self, fullname: str, path: str) -> None: ...
    def get_data(self, path: str) -> bytes: ...
    def get_filename(self, name: str | None = ...) -> str: ...
    def load_module(self, name: str | None = ...) -> types.ModuleType: ...

class ResourceReader(metaclass=ABCMeta):
    @abstractmethod
    def open_resource(self, resource: str) -> IO[bytes]: ...
    @abstractmethod
    def resource_path(self, resource: str) -> str: ...
    if sys.version_info >= (3, 10):
        @abstractmethod
        def is_resource(self, path: str) -> bool: ...
    else:
        @abstractmethod
        def is_resource(self, name: str) -> bool: ...

    @abstractmethod
    def contents(self) -> Iterator[str]: ...

if sys.version_info >= (3, 9):
    @runtime_checkable
    class Traversable(Protocol):
        @abstractmethod
        def is_dir(self) -> bool: ...
        @abstractmethod
        def is_file(self) -> bool: ...
        @abstractmethod
        def iterdir(self) -> Iterator[Traversable]: ...
        if sys.version_info >= (3, 11):
            @abstractmethod
            def joinpath(self, *descendants: str) -> Traversable: ...
        else:
            @abstractmethod
            def joinpath(self, child: str) -> Traversable: ...
        # The .open method comes from pathlib.pyi and should be kept in sync.
        @overload
        @abstractmethod
        def open(
            self,
            mode: OpenTextMode = ...,
            buffering: int = ...,
            encoding: str | None = ...,
            errors: str | None = ...,
            newline: str | None = ...,
        ) -> TextIOWrapper: ...
        # Unbuffered binary mode: returns a FileIO
        @overload
        @abstractmethod
        def open(
            self, mode: OpenBinaryMode, buffering: Literal[0], encoding: None = ..., errors: None = ..., newline: None = ...
        ) -> FileIO: ...
        # Buffering is on: return BufferedRandom, BufferedReader, or BufferedWriter
        @overload
        @abstractmethod
        def open(
            self,
            mode: OpenBinaryModeUpdating,
            buffering: Literal[-1, 1] = ...,
            encoding: None = ...,
            errors: None = ...,
            newline: None = ...,
        ) -> BufferedRandom: ...
        @overload
        @abstractmethod
        def open(
            self,
            mode: OpenBinaryModeWriting,
            buffering: Literal[-1, 1] = ...,
            encoding: None = ...,
            errors: None = ...,
            newline: None = ...,
        ) -> BufferedWriter: ...
        @overload
        @abstractmethod
        def open(
            self,
            mode: OpenBinaryModeReading,
            buffering: Literal[-1, 1] = ...,
            encoding: None = ...,
            errors: None = ...,
            newline: None = ...,
        ) -> BufferedReader: ...
        # Buffering cannot be determined: fall back to BinaryIO
        @overload
        @abstractmethod
        def open(
            self, mode: OpenBinaryMode, buffering: int = ..., encoding: None = ..., errors: None = ..., newline: None = ...
        ) -> BinaryIO: ...
        # Fallback if mode is not specified
        @overload
        @abstractmethod
        def open(
            self, mode: str, buffering: int = ..., encoding: str | None = ..., errors: str | None = ..., newline: str | None = ...
        ) -> IO[Any]: ...
        @property
        def name(self) -> str: ...
        @abstractmethod
        def __truediv__(self, child: str) -> Traversable: ...
        @abstractmethod
        def read_bytes(self) -> bytes: ...
        @abstractmethod
        def read_text(self, encoding: str | None = ...) -> str: ...

    class TraversableResources(ResourceReader):
        @abstractmethod
        def files(self) -> Traversable: ...
        def open_resource(self, resource: str) -> BufferedReader: ...  # type: ignore[override]
        def resource_path(self, resource: Any) -> NoReturn: ...
        def is_resource(self, path: str) -> bool: ...
        def contents(self) -> Iterator[str]: ...
