import json
import os
import re
import subprocess
import sys
import importlib.util

def main():
    # Determine root directory: parent of checks directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    subject_dir = os.path.join(root_dir, "subject")
    seconds_path = os.path.join(subject_dir, "seconds.py")
    test_path = os.path.join(subject_dir, "test_seconds.py")

    seconds_file_exists = os.path.isfile(seconds_path)
    test_file_exists = os.path.isfile(test_path)

    # Count assertions in test file
    test_assertion_count = 0
    if test_file_exists:
        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Count occurrences of assert* followed by a parenthesis
        test_assertion_count = len(re.findall(r"\bassert\w*\s*\(", content))

    # Compute to_seconds values
    to_seconds_values = {}
    if seconds_file_exists:
        try:
            spec = importlib.util.spec_from_file_location("seconds", seconds_path)
            seconds_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(seconds_mod)
            to_seconds = seconds_mod.to_seconds
            for h, m in [(0, 0), (1, 0), (1, 30), (2, 15)]:
                key = f"{h},{m}"
                to_seconds_values[key] = to_seconds(h, m)
        except Exception:
            # If the module cannot be loaded, leave values empty
            to_seconds_values = {}

    # Run unittest
    unittest_returncode = None
    if test_file_exists:
        cmd = [sys.executable, "-m", "unittest", "test_seconds"]
        try:
            result = subprocess.run(cmd, cwd=subject_dir, capture_output=True, text=True, timeout=30)
            unittest_returncode = result.returncode
        except Exception:
            unittest_returncode = -1
    else:
        unittest_returncode = -1

    output = {
        "seconds_file_exists": seconds_file_exists,
        "test_assertion_count": test_assertion_count,
        "test_file_exists": test_file_exists,
        "to_seconds_values": to_seconds_values,
        "unittest_returncode": unittest_returncode,
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()
