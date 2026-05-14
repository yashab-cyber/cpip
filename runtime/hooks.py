"""
Python import hooks for transparent cloud package loading.

Registers on sys.meta_path to intercept imports of packages that are
configured for cloud execution, creating proxy modules instead.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
from types import ModuleType
from typing import Any, Sequence

from shared.constants import CLOUD_PREFERRED_PACKAGES

# Global registry of cloud-configured packages
_cloud_packages: dict[str, dict[str, Any]] = {}
_hooks_active = False


def register_cloud_package(package: str, config: Any = None, hybrid: bool = False) -> None:
    """Register a package for cloud execution via import hooks."""
    _cloud_packages[package] = {
        "config": config,
        "hybrid": hybrid,
        "loaded": False,
    }


def activate_hooks(config: Any = None) -> None:
    """Activate cpip import hooks on sys.meta_path."""
    global _hooks_active
    if _hooks_active:
        return

    finder = CpipFinder(config)
    # Insert at position 0 to intercept before default finders
    # but we check our registry first, and fall back to standard if not ours
    sys.meta_path.insert(0, finder)
    _hooks_active = True


def deactivate_hooks() -> None:
    """Remove cpip import hooks from sys.meta_path."""
    global _hooks_active
    sys.meta_path[:] = [f for f in sys.meta_path if not isinstance(f, CpipFinder)]
    _hooks_active = False


class CpipFinder(importlib.abc.MetaPathFinder):
    """
    Custom meta path finder that intercepts imports for cloud-registered packages.

    When a registered package is imported, instead of failing (because it's
    not installed locally), we create a proxy module that transparently
    routes calls to the cloud execution engine.
    """

    def __init__(self, config: Any = None):
        self.config = config

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        """
        Find module spec for cloud-registered packages.

        Returns None for packages we don't handle (standard import continues).
        """
        # Check top-level package name
        top_level = fullname.split(".")[0]

        # Only intercept if explicitly registered for cloud execution
        if top_level not in _cloud_packages:
            return None

        # Don't intercept if already loaded normally
        if top_level in sys.modules and not isinstance(sys.modules[top_level], ProxyModule):
            return None

        # Create spec with our loader
        return importlib.machinery.ModuleSpec(
            fullname,
            CpipLoader(fullname, self.config, _cloud_packages.get(top_level, {})),
            is_package=(fullname == top_level),
        )

    def find_module(self, fullname: str, path: Sequence[str] | None = None) -> importlib.abc.Loader | None:
        """Legacy find_module for compatibility."""
        spec = self.find_spec(fullname, path)
        return spec.loader if spec else None


class CpipLoader(importlib.abc.Loader):
    """Loads cloud-proxied modules."""

    def __init__(self, fullname: str, config: Any, pkg_info: dict):
        self.fullname = fullname
        self.config = config
        self.pkg_info = pkg_info

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType | None:
        """Create a proxy module."""
        return ProxyModule(spec.name, self.config, self.pkg_info)

    def exec_module(self, module: ModuleType) -> None:
        """Execute module initialization (minimal for proxies)."""
        if isinstance(module, ProxyModule):
            module._initialized = True


class ProxyModule(ModuleType):
    """
    A proxy module that transparently routes attribute access and
    function calls to the cloud execution engine.

    Usage:
        import torch  # → creates ProxyModule
        x = torch.tensor([1,2,3])  # → cloud execution
        print(x)  # → result from cloud
    """

    def __init__(self, name: str, config: Any = None, pkg_info: dict | None = None):
        super().__init__(name)
        self.__name__ = name
        self.__package__ = name.split(".")[0]
        self.__path__ = []  # Mark as package
        self.__loader__ = None
        self.__spec__ = None
        self._config = config
        self._pkg_info = pkg_info or {}
        self._initialized = False
        self._session = None
        self._submodules: dict[str, ProxyModule] = {}

    def _get_session(self):
        """Get or create cloud execution session."""
        if self._session is None:
            from runtime.interceptor import CloudSession
            self._session = CloudSession(self._config)
        return self._session

    def __getattr__(self, name: str) -> Any:
        """Intercept attribute access and route to cloud."""
        if name.startswith("_"):
            raise AttributeError(name)

        # Submodule access (e.g., torch.nn)
        submodule_name = f"{self.__name__}.{name}"
        if submodule_name not in self._submodules:
            # Try as callable first, then as submodule
            return ProxyCallable(self._get_session(), submodule_name)

        return self._submodules[submodule_name]

    def __repr__(self) -> str:
        return f"<cpip.ProxyModule '{self.__name__}' (cloud)>"

    def __dir__(self) -> list[str]:
        """Return available attributes (query cloud for module dir)."""
        session = self._get_session()
        try:
            return session.get_module_dir(self.__name__)
        except Exception:
            return []


class ProxyCallable:
    """
    A proxy for remote callable objects (functions, classes, methods).

    When called, serializes arguments and sends to cloud for execution.
    """

    def __init__(self, session: Any, name: str):
        self._session = session
        self._name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the remote function/method."""
        return self._session.execute(self._name, args, kwargs)

    def __getattr__(self, name: str) -> ProxyCallable:
        """Chain attribute access (e.g., torch.nn.functional.relu)."""
        return ProxyCallable(self._session, f"{self._name}.{name}")

    def __repr__(self) -> str:
        return f"<cpip.ProxyCallable '{self._name}'>"
