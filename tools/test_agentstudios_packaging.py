"""Package-data declarations cover the actual AgentStudios browser assets.

This small regression guard supplements, but does not replace, building and
rendering the installed wheel outside the source checkout.
"""
from pathlib import Path
import unittest

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from loop_engine.core.service_runtime import agentstudios_pages as pages


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/loop_engine"
PREFIX = "core/service_runtime/web_assets/agentstudios/"


def uncovered_assets(patterns):
    # Filesystem glob semantics matter: a single '*' never spans a directory,
    # unlike fnmatchcase, which would miss the very regression this checks.
    covered = {path.relative_to(PACKAGE).as_posix()
               for pattern in patterns for path in PACKAGE.glob(pattern) if path.is_file()}
    return {PREFIX + name for name in pages.ASSETS
            if (PACKAGE / PREFIX / name).is_file() and PREFIX + name not in covered}


class AgentStudiosPackagingTests(unittest.TestCase):
    def test_renderer_assets_are_declared_for_wheel_installation(self):
        configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        patterns = configuration["tool"]["setuptools"]["package-data"]["loop_engine"]
        self.assertEqual(uncovered_assets(patterns), set())
        mark = PREFIX + "mark.svg"
        # Removing its declared coverage must expose the installed-only
        # failure even though the mark remains present in the source tree.
        without_mark = [pattern for pattern in patterns if PACKAGE / mark not in PACKAGE.glob(pattern)]
        self.assertEqual(uncovered_assets(without_mark), {mark})


if __name__ == "__main__":
    unittest.main()
