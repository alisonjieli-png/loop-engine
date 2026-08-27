"""Template intelligence: typed task templates with JSON bindings.

Templates are Code Intelligence records (procedural knowledge), not a
fifth intelligence layer. A template standardizes freeform text into
typed variables: task type, output requested, file paths, links, and
constraints. The original input is always preserved alongside the
normalized interpretation.

Templates are data. Binding a task to a template is a governed Loop
operation. A template never grants permissions, never erases a user
requirement, and never promotes itself.
"""
from __future__ import annotations

from importlib import import_module as _import_module

_PUBLIC = {
    "TaskTemplate": ("model", "TaskTemplate"),
    "TemplateBinding": ("model", "TemplateBinding"),
    "CompiledTask": ("model", "CompiledTask"),
    "BINDING_MODES": ("model", "BINDING_MODES"),
    "TemplateLibrary": ("library", "TemplateLibrary"),
    "CORE_TEMPLATES": ("library", "CORE_TEMPLATES"),
    "compile_task": ("compiler", "compile_task"),
}

__all__ = tuple(_PUBLIC)


def __getattr__(name: str):
    target = _PUBLIC.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = target
    return getattr(_import_module(f"{__name__}.{module}"), attribute)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_PUBLIC))
