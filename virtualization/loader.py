"""
Lazy module loader.

Defers actual module loading until first attribute access,
fetching package content from cloud on demand.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
from types import ModuleType
from typing import Any


class LazyModule(ModuleType):
    """Module that loads its content on first attribute access."""

    def __init__(self, name: str, fetch_func=None):
        super().__init__(name)
        self.__name__ = name
        self.__path__ = []
        self.__package__ = name.split(".")[0]
        self._fetch_func = fetch_func
        self._loaded = False
        self._real_module: ModuleType | None = None

    def _ensure_loaded(self) -> None:
        """Load the real module on first access."""
        if self._loaded:
            return
        self._loaded = True
        if self._fetch_func:
            self._real_module = self._fetch_func(self.__name__)
            if self._real_module:
                self.__dict__.update(self._real_module.__dict__)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        self._ensure_loaded()
        if self._real_module:
            return getattr(self._real_module, name)
        raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "lazy"
        return f"<LazyModule '{self.__name__}' ({status})>"


class LazyFinder(importlib.abc.MetaPathFinder):
    """Finder that creates lazy-loaded modules for virtualized packages."""

    def __init__(self, registry: dict[str, Any]):
        self._registry = registry

    def find_spec(self, fullname, path=None, target=None):
        top = fullname.split(".")[0]
        if top not in self._registry:
            return None
        return importlib.machinery.ModuleSpec(
            fullname,
            LazyLoader(self._registry, fullname),
            is_package=(fullname == top),
        )


class LazyLoader(importlib.abc.Loader):
    """Loader that creates LazyModule instances."""

    def __init__(self, registry: dict[str, Any], fullname: str):
        self._registry = registry
        self._fullname = fullname

    def create_module(self, spec):
        return LazyModule(spec.name, self._registry.get("fetch_func"))

    def exec_module(self, module):
        pass
