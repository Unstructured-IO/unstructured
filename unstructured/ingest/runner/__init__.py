import importlib.util as import_utils
import pkgutil
import sys
from importlib.machinery import ModuleSpec, SourceFileLoader
from typing import Optional

__all__ = []


def _import_modules():
    module_name: str
    is_pkg: bool
    for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
        if is_pkg:
            # Ignore packages from being dynamically added
            return

        spec: Optional[ModuleSpec] = import_utils.spec_from_loader(
            module_name,
            loader.find_module(module_name),  # type: ignore
        )
        if not spec:
            return
        module = import_utils.module_from_spec(spec)
        spec_loader: Optional[SourceFileLoader] = spec.loader  # type: ignore
        if not spec_loader:
            return
        spec_loader.exec_module(module)
        if hasattr(module, module_name):
            __all__.append(module_name)
            sys.modules[module_name] = getattr(module, module_name)
            current_module = sys.modules[__name__]
            setattr(current_module, module_name, getattr(module, module_name))


_import_modules()
