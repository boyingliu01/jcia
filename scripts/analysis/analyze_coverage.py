#!/usr/bin/env python3
"""Analyze coverage report and identify files needing improvement."""

import json
import sys

def analyze_coverage(coverage_file='report/coverage.json'):
    """Analyze coverage report and print low coverage files."""
    with open(coverage_file, 'r') as f:
        data = json.load(f)

    files = data.get('files', {})

    print('=' * 80)
    print('COVERAGE ANALYSIS REPORT')
    print('=' * 80)
    print()

    # Overall coverage
    totals = data.get('totals', {})
    print(f"Overall Coverage: {totals.get('percent_covered', 0):.2f}%")
    print(f"Total Lines: {totals.get('num_lines', 0)}")
    print(f"Missing Lines: {totals.get('missing_lines', 0)}")
    print()

    # Files with <80% coverage
    print('-' * 80)
    print('FILES WITH < 80% COVERAGE (Need Improvement)')
    print('-' * 80)

    low_coverage_files = []
    for filepath, info in sorted(files.items()):
        pct = info.get('summary', {}).get('percent_covered', 0)
        if pct < 80:
            low_coverage_files.append((filepath, pct, info))

    if low_coverage_files:
        for filepath, pct, info in low_coverage_files:
            summary = info.get('summary', {})
            print(f"  {filepath}")
            print(f"    Coverage: {pct:.1f}%")
            print(f"    Lines: {summary.get('num_lines', 0)}, Missing: {summary.get('missing_lines', 0)}")
            print()
    else:
        print("  All files have >= 80% coverage!")

    print()

    # Files with <70% coverage (critical)
    print('-' * 80)
    print('FILES WITH < 70% COVERAGE (Critical - Priority)')
    print('-' * 80)

    critical_files = [(f, p, i) for f, p, i in low_coverage_files if p < 70]

    if critical_files:
        for filepath, pct, info in critical_files:
            print(f"  {filepath}: {pct:.1f}%")
    else:
        print("  No files with < 70% coverage.")

    print()
    print('=' * 80)

    # Summary stats
    total_files = len(files)
    files_80_plus = sum(1 for f, p, i in low_coverage_files if p >= 80) + (total_files - len(low_coverage_files))
    files_70_80 = sum(1 for f, p, i in low_coverage_files if 70 <= p < 80)
    files_below_70 = len(critical_files)

    print('SUMMARY')
    print('=' * 80)
    print(f"Total Files: {total_files}")
    print(f"Files >= 80%: {total_files - len(low_coverage_files)} ({((total_files - len(low_coverage_files)) / total_files * 100):.1f}%)")
    print(f"Files 70-80%: {files_70_80} ({(files_70_80 / total_files * 100):.1f}%)")
    print(f"Files < 70%: {files_below_70} ({(files_below_70 / total_files * 100):.1f}%)")
    print()

    return totals.get('percent_covered', 0)

if __name__ == '__main__':
    coverage_file = sys.argv[1] if len(sys.argv) > 1 else 'report/coverage.json'
    overall = analyze_coverage(coverage_file)
    sys.exit(0 if overall >= 80 else 1)
