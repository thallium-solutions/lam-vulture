#!/usr/bin/env python3
"""Compile and run @lam/vulture's migrated end-to-end tests in isolation."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
COMPILER = "lamc"
MIN_COMPILER_VERSION = (1, 18, 0)
PACKAGE_PATH = Path("@lam") / "vulture"
VERSION_PATTERN = re.compile(r"(?:lamc\s+)?v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?")


def run_command(
    command: list[str], *, cwd: Path, timeout: int
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def require_compiler() -> str:
    compiler = shutil.which(COMPILER)
    if compiler is None:
        raise SystemExit("error: lamc is required but was not found on PATH")

    try:
        result = run_command([compiler, "version"], cwd=PACKAGE_ROOT, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"error: unable to run 'lamc version': {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        raise SystemExit(f"error: unable to check lamc version: {detail}")

    version_text = result.stdout.strip()
    match = VERSION_PATTERN.fullmatch(version_text)
    if match is None:
        raise SystemExit(f"error: unrecognized lamc version output: {version_text!r}")

    version = tuple(int(part) for part in match.groups())
    if version < MIN_COMPILER_VERSION:
        required = ".".join(str(part) for part in MIN_COMPILER_VERSION)
        raise SystemExit(
            f"error: @lam/vulture tests require lamc >= {required}; found {version_text}"
        )
    return compiler


def extract_expected(source: str) -> str | None:
    """Read repeated or block-form ``# expect:`` directives."""
    expected: list[str] = []
    in_block = False
    for line in source.splitlines():
        match = re.match(r"^\s*#\s*expect:\s*(.*)$", line)
        if match:
            text = match.group(1)
            if text:
                expected.append(text)
                in_block = False
            else:
                in_block = True
            continue

        if not in_block:
            continue
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            in_block = False
            continue
        if re.match(r"^\s*#\s*end-expect\s*$", line):
            in_block = False
            continue
        text = stripped[1:]
        if text.startswith(" "):
            text = text[1:]
        expected.append(text)

    return "\n".join(expected).strip() if expected else None


def stage_package(extlibs: Path) -> None:
    destination = extlibs / PACKAGE_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        PACKAGE_ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            "build",
            "extlibs",
            "*.lamc-cache",
            "__pycache__",
            "*.pyc",
        ),
    )


def process_failure(label: str, result: subprocess.CompletedProcess[str]) -> str:
    details = [f"{label} (exit {result.returncode})"]
    if result.stdout.strip():
        details.append("stdout:\n" + result.stdout.rstrip())
    if result.stderr.strip():
        details.append("stderr:\n" + result.stderr.rstrip())
    return "\n".join(details)


def run_case(
    compiler: str, case: Path, *, workspace: Path, extlibs: Path
) -> tuple[bool, str]:
    expected = extract_expected(case.read_text(encoding="utf-8"))
    if expected is None:
        return False, "TEST ERROR: no '# expect:' output found"

    binary = workspace / case.stem
    compile_command = [
        compiler,
        str(case),
        "--extlibs",
        str(extlibs),
        "--no-cache",
        "-o",
        str(binary),
    ]
    try:
        compiled = run_command(compile_command, cwd=workspace, timeout=300)
    except subprocess.TimeoutExpired:
        return False, "COMPILE FAIL: timed out after 300 seconds"
    except OSError as exc:
        return False, f"COMPILE FAIL: {exc}"
    if compiled.returncode != 0:
        return False, process_failure("COMPILE FAIL", compiled)

    try:
        executed = run_command([str(binary)], cwd=workspace, timeout=90)
    except subprocess.TimeoutExpired:
        return False, "RUN FAIL: timed out after 90 seconds"
    except OSError as exc:
        return False, f"RUN FAIL: {exc}"
    if executed.returncode != 0:
        return False, process_failure("RUN FAIL", executed)

    actual = executed.stdout.rstrip("\n")
    if actual != expected:
        details = [
            "OUTPUT MISMATCH",
            f"expected: {expected!r}",
            f"actual:   {actual!r}",
        ]
        if executed.stderr:
            details.append(f"stderr:   {executed.stderr.rstrip()!r}")
        return False, "\n".join(details)
    return True, "output matches"


def main() -> int:
    parser = argparse.ArgumentParser(description="@lam/vulture package tests")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--filter", "-f", help="run test files containing this text")
    args = parser.parse_args()

    compiler = require_compiler()
    cases = sorted(TEST_ROOT.glob("test_*.lam"))
    if args.filter:
        needle = args.filter.lower()
        cases = [case for case in cases if needle in case.name.lower()]
    if not cases:
        print("error: no matching @lam/vulture test cases found", file=sys.stderr)
        return 2

    failures: list[tuple[Path, str]] = []
    with tempfile.TemporaryDirectory(prefix="lam-vulture-tests-") as temporary:
        workspace = Path(temporary)
        extlibs = workspace / "extlibs"
        stage_package(extlibs)

        print(f"Running {len(cases)} @lam/vulture test(s)...\n")
        for case in cases:
            passed, message = run_case(
                compiler, case, workspace=workspace, extlibs=extlibs
            )
            relative = case.relative_to(PACKAGE_ROOT)
            print(f"  {'PASS' if passed else 'FAIL'}  {relative}", flush=True)
            if not passed:
                failures.append((relative, message))
                if args.verbose:
                    for line in message.splitlines():
                        print(f"        {line}")

    passed_count = len(cases) - len(failures)
    print(
        f"\n@lam/vulture results: {passed_count} passed, "
        f"{len(failures)} failed, {len(cases)} total"
    )
    if failures and not args.verbose:
        print("Re-run with --verbose for failure details.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
