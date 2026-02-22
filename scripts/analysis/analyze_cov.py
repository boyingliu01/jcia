#!/usr/bin/env python
"""Analyze coverage report."""
import json

with open('report/coverage.json') as f:
    data = json.load(f)

print("="*60)
print("COVERAGE ANALYSIS")
print("="*60)
print(f"\nOverall Coverage: {data['totals']['percent_covered']:.2f}%")
print(f"Total Lines: {data['totals']['num_lines']}")
print(f"Missing Lines: {data['totals']['missing_lines']}")

print("\n" + "-"*60)
print("FILES WITH < 80% COVERAGE")
print("-"*60)

low_cov = []
for path, info in sorted(data['files'].items()):
    pct = info['summary']['percent_covered']
    if pct < 80:
        low_cov.append((path, pct, info))

if low_cov:
    for path, pct, info in sorted(low_cov, key=lambda x: x[1]):
        summary = info['summary']
        print(f"\n{path}")
        print(f"  Coverage: {pct:.1f}% ({summary['covered_lines']}/{summary['num_lines']} lines)")
        print(f"  Missing: {summary['missing_lines']} lines")
else:
    print("All files have >= 80% coverage!")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
total = len(data['files'])
print(f"Total Files: {total}")
print(f">= 80%: {total - len(low_cov)} ({(total - len(low_cov))/total*100:.1f}%)")
print(f"< 80%: {len(low_cov)} ({len(low_cov)/total*100:.1f}%)")

# Target to reach 80%
current = data['totals']['percent_covered']
target = 80.0
print(f"\nCurrent: {current:.2f}%")
print(f"Target: {target:.2f}%")
print(f"Gap: {target - current:.2f}%")
