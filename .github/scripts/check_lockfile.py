#!/usr/bin/env python3
"""Lockfile drift gate for requirements.lock / requirements.txt.

Default mode (constraint check, used by CI):
  Every requirement in requirements.txt must be satisfied by the exact pins in
  requirements.lock. This catches "edited the ranges, never regenerated the
  lock" — the drift failure mode — deterministically and offline. Upstream
  releasing newer versions within range is staleness (Dependabot's job), not
  drift, and does not fail the gate.

Strict mode (--strict, local use):
  Recompiles requirements.txt with uv and requires byte-identical output.
  Proves provenance (lock was really produced by the documented command).
  Use right after regenerating; time-sensitive, hence not the CI gate.

Exit codes: 0 = in sync, 1 = drift/missing, 2 = tooling error.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet
    from packaging.utils import canonicalize_name
    from packaging.version import Version
except ImportError:  # pragma: no cover
    print("packaging is required: pip install packaging", file=sys.stderr)
    raise SystemExit(2)

LOCK = "requirements.lock"
SRC = "requirements.txt"
PLATFORM = "linux"

PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^ \t#]+)")


def load_source_requirements(repo: Path) -> list[Requirement]:
    reqs: list[Requirement] = []
    for raw in (repo / SRC).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # strip trailing inline comments: "pkg>=1  # note"
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        if not line or line.startswith("-"):  # options like -r/-e/--hash handled by compiler
            continue
        reqs.append(Requirement(line))
    return reqs


def norm(name: str) -> str:
    """PEP 503 name normalization (uv writes dashed names: jaraco-context)."""
    return canonicalize_name(name)


def load_lock_pins(repo: Path) -> dict[str, Version]:
    pins: dict[str, Version] = {}
    for raw in (repo / LOCK).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = PIN_RE.match(line)
        if m:
            name, ver = m.groups()
            pins[norm(name)] = Version(ver)
    return pins


def constraint_check(repo: Path) -> tuple[str, list[str]]:
    """Return (status, problems)."""
    lock = repo / LOCK
    src = repo / SRC
    if not src.exists():
        return "MISSING-SRC", [f"{SRC} not found"]
    if not lock.exists():
        return "MISSING-LOCK", [f"{LOCK} not found"]

    pins = load_lock_pins(repo)
    if not pins:
        return "EMPTY-LOCK", [f"{LOCK} contains no pinned versions"]

    problems: list[str] = []
    for req in load_source_requirements(repo):
        key = norm(req.name)
        if key not in pins:
            problems.append(f"{req.name} not pinned in {LOCK} (required: {req.specifier})")
            continue
        ver = pins[key]
        if ver not in SpecifierSet(str(req.specifier)):
            problems.append(f"{req.name}=={ver} violates required {req.specifier}")
    return ("OK", []) if not problems else ("DRIFT", problems)


def strict_check(repo: Path, py: str) -> tuple[str, list[str]]:
    """Recompile with uv and compare bytes against the committed lock."""
    lock = repo / LOCK
    if not (repo / SRC).exists():
        return "MISSING-SRC", [f"{SRC} not found"]
    if not lock.exists():
        return "MISSING-LOCK", [f"{LOCK} not found"]
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "expected.lock"
        proc = subprocess.run(
            [
                "uv", "pip", "compile", SRC,
                "-o", str(out), "--quiet", "--no-header", "--strip-extras",
                "--python-version", py, "--python-platform", PLATFORM,
            ],
            cwd=repo, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            return "COMPILE-ERROR", [proc.stderr.strip()[:800]]
        expected = out.read_text(encoding="utf-8")
    actual = lock.read_text(encoding="utf-8")
    if expected == actual:
        return "OK", []
    exp_lines = set(expected.splitlines())
    act_lines = set(actual.splitlines())
    diffs = [f"+ {l}" for l in sorted(exp_lines - act_lines)[:6]]
    diffs += [f"- {l}" for l in sorted(act_lines - exp_lines)[:6]]
    return "STRICT-DRIFT", diffs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repos", nargs="*", default=["."])
    ap.add_argument("--strict", action="store_true",
                    help="byte-compare against a fresh uv compile (local use)")
    ap.add_argument("--python-version", default="3.11",
                    help="python-version for --strict compile (default: %(default)s; "
                         "use 3.12 for repos with 3.12+ floors)")
    args = ap.parse_args()

    failures = 0
    for repo in (Path(a) for a in args.repos):
        if args.strict:
            status, problems = strict_check(repo, args.python_version)
        else:
            status, problems = constraint_check(repo)

        if status == "OK":
            print(f"OK {repo.name}")
            continue
        failures += 1
        print(f"{status} {repo.name}:")
        for p in problems[:10]:
            print(f"  {p}")
        if status == "DRIFT":
            print(f"  -> regenerate: uv pip compile {SRC} -o {LOCK} "
                  f"--quiet --no-header --strip-extras "
                  f"--python-version {args.python_version} --python-platform {PLATFORM}")
        print()

    if failures:
        print(f"{failures} repo(s) out of sync.")
        return 1
    print("All lockfiles in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
