"""Import-boundary checks for the typed decision provider package.

These checks inspect the exact source tree without importing a provider or
executing a request. Package ownership and one-way dependencies are enforced
separately from behavioral tests and live integration qualification.
"""
import ast
from pathlib import Path
import unittest


class DecisionBoundaryChecks(unittest.TestCase):
    def test_core_decisions_do_not_depend_on_application_or_cli(self):
        root = Path(__file__).resolve().parents[1] / "src/loop_engine/core/decisions"
        sources = list(root.glob("*.py"))
        self.assertGreaterEqual(len(sources), 6)
        for path in sources:
            for item in ast.walk(ast.parse(path.read_text())):
                if isinstance(item, ast.ImportFrom):
                    self.assertNotIn("code_nodes", item.module or "", str(path))
                    self.assertNotIn("decision_cli", item.module or "", str(path))
                if isinstance(item, ast.Import):
                    self.assertFalse(any("code_nodes" in alias.name or "decision_cli" in alias.name
                                         for alias in item.names), str(path))

    def test_decision_package_creates_no_parallel_runtime_or_store(self):
        root = Path(__file__).resolve().parents[1] / "src/loop_engine/core/decisions"
        for path in root.glob("*.py"):
            for item in ast.walk(ast.parse(path.read_text())):
                if isinstance(item, ast.ClassDef):
                    self.assertFalse(item.name.endswith("Node"), str(path))
                    self.assertNotIn(item.name, ("Loop", "ProviderRegistry", "RunHistory", "CredentialStore"))

    def test_shared_protocol_and_transport_do_not_depend_on_provider_adapters(self):
        root = Path(__file__).resolve().parents[1] / "src/loop_engine/core/decisions"
        for name in ("contracts.py", "credentials.py", "wire.py", "http_transport.py"):
            for item in ast.walk(ast.parse((root / name).read_text())):
                if isinstance(item, ast.ImportFrom):
                    self.assertNotIn(item.module, ("jev", "system_one", "configuration", "gateway"), name)

    def test_generic_endpoint_does_not_import_jev_or_load_models(self):
        root = Path(__file__).resolve().parents[1] / "src/loop_engine/core/decisions"
        for item in ast.walk(ast.parse((root / "system_one.py").read_text())):
            if isinstance(item, ast.ImportFrom):
                self.assertNotIn(item.module, ("jev", "torch", "transformers", "s1proto.scorer"))

    def test_configuration_and_adapters_do_not_own_network_or_process_clients(self):
        root = Path(__file__).resolve().parents[1] / "src/loop_engine/core/decisions"
        blocked = {"httpx", "requests", "socket", "subprocess", "torch", "transformers"}
        for name in ("configuration.py", "system_one.py", "jev.py", "credentials.py", "wire.py",
                     "command_risk_policy.py", "command_risk_programs.py", "stations.py", "rules_engine.py",
                     "station_engines.py"):
            for item in ast.walk(ast.parse((root / name).read_text())):
                if isinstance(item, ast.Import):
                    self.assertFalse({alias.name.split('.')[0] for alias in item.names} & blocked, name)
                if isinstance(item, ast.ImportFrom):
                    self.assertNotIn((item.module or '').split('.')[0], blocked, name)
                    if (item.module or '').startswith('urllib'):
                        self.assertEqual(item.module, 'urllib.parse', name)


    def test_the_command_risk_policy_never_runs_what_it_reads(self):
        root = Path(__file__).resolve().parents[1] / "src/loop_engine/core/decisions"
        for name in ("command_risk_policy.py", "command_risk_programs.py"):
            tree = ast.parse((root / name).read_text())
            calls = {node.func.attr for node in ast.walk(tree)
                     if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
            self.assertFalse(calls & {"system", "popen", "run", "Popen", "check_output", "check_call", "exec"}, name)
            imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
                        for alias in node.names}
            self.assertLessEqual(imported, {"hashlib", "os", "re", "shlex"}, name)


if __name__ == "__main__":
    unittest.main()
