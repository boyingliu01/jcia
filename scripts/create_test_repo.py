"""Create a minimal test Java repository with Maven structure."""

import os
import subprocess
from pathlib import Path

# Create directory structure
base_dir = Path("tests/test_data/jenkins_test_repo")
base_dir.mkdir(parents=True, exist_ok=True)

# Create Maven project structure
dirs = [
    "src/main/java/com/example/jcia",
    "src/test/java/com/example/jcia",
    "src/main/resources",
]

for d in dirs:
    (base_dir / d).mkdir(parents=True, exist_ok=True)

print("Created directory structure for test repository")
