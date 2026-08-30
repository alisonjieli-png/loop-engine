from pathlib import Path
source = Path("inputs/failing_package")
target = Path("repaired_package")
target.mkdir()
original = (source / "calc.py").read_text()
patched = original.replace("return left - right", "return left + right")
assert patched != original
(target / "calc.py").write_text(patched)
(target / "test_calc.py").write_text((source / "test_calc.py").read_text())
print("repair applied")
