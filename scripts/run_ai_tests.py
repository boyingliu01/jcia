import subprocess
import sys

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/adapters/test_ai/test_volcengine_adapter.py",
        "-v",
        "--tb=short",
    ],
    capture_output=True,
    text=True,
)

print(result.stdout)
print(result.stderr, file=sys.stderr)
sys.exit(result.returncode)
