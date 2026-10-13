#!/usr/bin/env python3
"""Run the protocol tests (stdlib unittest) and optionally write a JUnit XML report for check_trace.py.

  python3 tests/protocol/run.py                          # run everything
  python3 tests/protocol/run.py --junit report.xml       # also write JUnit XML
  python3 -m unittest discover -s tests/protocol         # the plain unittest way (no report)

Test names carry the rule ids they cover with underscores (test_CORE_SRV_030_...); the report writes them
with hyphens (CORE-SRV-030) so generator/scripts/check_trace.py finds them: check_trace.py --junit server=report.xml
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ID_UNDERSCORED = re.compile(r"(?<![A-Za-z0-9])(CORE|PLAT|EXT)_([A-Z0-9]+)_([0-9]{3})(?![0-9])")


def hyphenate(name: str) -> str:
    """test_CORE_SRV_030_x -> test_CORE-SRV-030_x (rule ids only)."""
    return ID_UNDERSCORED.sub(r"\1-\2-\3", name)


class Result(unittest.TextTestResult):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.records = []  # (test, seconds, outcome, detail)
        self._t0 = 0.0

    def startTest(self, test):
        self._t0 = time.monotonic()
        super().startTest(test)

    def _add(self, test, outcome, detail=""):
        self.records.append((test, time.monotonic() - self._t0, outcome, detail))

    def addSuccess(self, test):
        super().addSuccess(test)
        self._add(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._add(test, "failure", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._add(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._add(test, "skipped", reason)


def junit(records) -> ET.ElementTree:
    root = ET.Element("testsuite", name="protocol", tests=str(len(records)),
                      failures=str(sum(r[2] == "failure" for r in records)),
                      errors=str(sum(r[2] == "error" for r in records)),
                      skipped=str(sum(r[2] == "skipped" for r in records)))
    for test, seconds, outcome, detail in records:
        cls = f"{type(test).__module__}.{type(test).__name__}"
        case = ET.SubElement(root, "testcase", classname=cls, name=hyphenate(test._testMethodName),
                             time=f"{seconds:.3f}")
        if outcome in ("failure", "error"):
            ET.SubElement(case, outcome, message=outcome).text = detail
        elif outcome == "skipped":
            ET.SubElement(case, "skipped", message=detail)
    ET.indent(root)
    return ET.ElementTree(root)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--junit", help="write a JUnit XML report here")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    sys.path.insert(0, str(HERE))
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py", top_level_dir=str(HERE))
    runner = unittest.TextTestRunner(resultclass=Result, verbosity=2 if args.verbose else 1, buffer=True)
    result = runner.run(suite)
    if args.junit:
        Path(args.junit).parent.mkdir(parents=True, exist_ok=True)
        junit(result.records).write(args.junit, encoding="utf-8", xml_declaration=True)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    sys.exit(main())
