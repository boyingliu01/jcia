"""Demo script for JCIA impact analysis using GitHub API."""

import requests
from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.core.entities.change_set import ChangeType

# The commit found from GitHub API that has Java changes
# PR #26284: "Avoid emitting console hyperlinks for upstream build causes"
# Commit: 680e107e68ea61a2f721e224bd236528d2989c60

commit_hash = "680e107e68ea61a2f721e224bd236528d2989c60"
pr_url = "https://github.com/jenkinsci/jenkins/pull/26284"

# Get commit details from GitHub API
api_url = f"https://api.github.com/repos/jenkinsci/jenkins/commits/{commit_hash}"
print(f"Fetching commit info from: {api_url}")

response = requests.get(api_url, timeout=10)
commit_data = response.json()

print("\n" + "=" * 80)
print("COMMIT ANALYSIS FROM GITHUB API")
print("=" * 80)
print(f"Commit Hash: {commit_hash}")
print(f"Title: {commit_data['commit']['message']}")
print(f"Author: {commit_data['commit']['author']['name']}")
print(f"Date: {commit_data['commit']['author']['date']}")
print(f"URL: {commit_data['html_url']}")

print("\n" + "-" * 80)
print("CHANGED FILES")
print("-" * 80)
if "files" in commit_data:
    for file_change in commit_data["files"]:
        status = file_change["status"]
        filename = file_change["filename"]
        additions = file_change.get("additions", 0)
        deletions = file_change.get("deletions", 0)
        print(f"  [{status}] {filename}")
        print(f"         +{additions} -{deletions} lines")

# Count Java files
java_files = [f for f in commit_data.get("files", []) if f.get("filename", "").endswith(".java")]
test_files = [f for f in commit_data.get("files", []) if "/test/" in f.get("filename", "")]

print(f"\nSummary:")
print(f"  Total files changed: {len(commit_data.get('files', []))}")
print(f"  Java files changed: {len(java_files)}")
print(f"  Test files changed: {len(test_files)}")
print(f"\nPR URL: {pr_url}")
