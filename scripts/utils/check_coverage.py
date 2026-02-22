#!/usr/bin/env python
"""Simple script to check coverage."""
import json

with open('coverage.json') as f:
    data = json.load(f)

print("Overall coverage: {}%".format(data['totals']['percent_covered']))
print("Files with <80% coverage:")
for path, info in sorted(data['files'].items()):
    pct = info['summary']['percent_covered']
    if pct < 80:
        print(f"  {path}: {pct:.1f}%")
