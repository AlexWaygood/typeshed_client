"""Module responsible for resolving names to the module they come from."""

import ast
from typing import Dict, List, NamedTuple, Optional, Union

from .finder import SearchContext, get_search_context, ModulePath
from . import parser


class ImportedInfo(NamedTuple):
    source_module: ModulePath
    info: parser.NameInfo


ResolvedName = Union[None, ModulePath, ImportedInfo, parser.NameInfo]


class Resolver:
    def __init__(self, search_context: Optional[SearchContext] = None) -> None:
        if search_context is None:
            search_context = get_search_context()
        self.ctx = search_context
        self._module_cache: Dict[ModulePath, Module] = {}

    def get_module(self, module_name: ModulePath) -> "Module":
        if module_name not in self._module_cache:
            names = parser.get_stub_names(
                ".".join(module_name), search_context=self.ctx
            )
            exists = names is not None
            if names is None:
                names = {}
            self._module_cache[module_name] = Module(names, self.ctx, exists=exists)
        return self._module_cache[module_name]

    def get_name(self, module_name: ModulePath, name: str) -> ResolvedName:
        module = self.get_module(module_name)
        return module.get_name(name, self)

    def get_fully_qualified_name(self, name: str) -> ResolvedName:
        """Public API."""
        *path, tail = name.split(".")
        return self.get_name(ModulePath(tuple(path)), tail)


class Module:
    def __init__(
        self, names: parser.NameDict, ctx: SearchContext, *, exists: bool = True
    ) -> None:
        self.names = names
        self.ctx = ctx
        self._name_cache: Dict[str, ResolvedName] = {}
        self.exists = exists

    def get_name(self, name: str, resolver: Resolver) -> ResolvedName:
        if name not in self._name_cache:
            self._name_cache[name] = self._uncached_get_name(name, resolver)
        return self._name_cache[name]

    def get_dunder_all(self, resolver: Resolver) -> Optional[List[str]]:
        """Return the contents of __all__, or None if it does not exist."""
        resolved_name = self.get_name("__all__", resolver)
        if resolved_name is None:
            return None
        if isinstance(resolved_name, ImportedInfo):
            resolved_name = resolved_name.info
        if not isinstance(resolved_name, parser.NameInfo):
            raise parser.InvalidStub(f"Invalid __all__: {resolved_name}")
        if isinstance(resolved_name.ast, parser.OverloadedName):
            names = []
            for defn in resolved_name.ast.definitions:
                subnames = self._get_dunder_all_from_ast(defn)
                if subnames is None:
                    raise parser.InvalidStub(f"Invalid __all__: {resolved_name}")
                names += subnames
            return names
        if isinstance(resolved_name.ast, parser.ImportedName):
            raise parser.InvalidStub(f"Invalid __all__: {resolved_name}")
        return self._get_dunder_all_from_ast(resolved_name.ast)

    def _get_dunder_all_from_ast(self, node: ast.AST) -> Optional[List[str]]:
        if not isinstance(node, (ast.Assign, ast.AugAssign)):
            return None
        rhs = node.value
        if not isinstance(rhs, ast.List):
            return None
        names = []
        for elt in rhs.elts:
            if not isinstance(elt, ast.Str):
                return None
            names.append(elt.s)
        return names

    def _uncached_get_name(self, name: str, resolver: Resolver) -> ResolvedName:
        if name not in self.names:
            return None
        info = self.names[name]
        if not isinstance(info.ast, parser.ImportedName):
            return info
        # TODO prevent infinite recursion
        import_info = info.ast
        if import_info.name is not None:
            module_path = ModulePath((*import_info.module_name, import_info.name))
            module = resolver.get_module(module_path)
            if module.exists:
                return module_path
            resolved = resolver.get_name(import_info.module_name, import_info.name)
            if isinstance(resolved, parser.NameInfo):
                return ImportedInfo(import_info.module_name, resolved)
            else:
                # TODO: preserve export information
                return resolved
        else:
            return import_info.module_name
