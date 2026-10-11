# DEAD-WEIGHT PURGE v2.0 AUDIT REPORT

**Repository**: `Statlas`  
**Mode**: `AUDIT_ONLY` (Zero repository modifications performed)  
**Baseline Commit SHA**: `92ea2adf48abf50684b07a097ba19e7a41673289`  
**Audit Date**: 2026-10-11  
**Verdict**: **YELLOW** (Dead weight detected; review recommended)

---

## 1. Executive Summary

- **Tracked Files in Git**: 579
- **Untracked Local Files**: 0
- **Total LOC**: 1,07,749
- **Analyzed Size**: 3.90 MB
- **Total Dead-Weight Candidates Identified**: 256
  - **Tier 0 (Provable Junk/Empty)**: 67
  - **Tier 1 (High Confidence)**: 3
  - **Tier 2 (Medium / Needs Verification)**: 186
  - **Tier 3 (Protected / Hard Vetoed)**: 0

## 2. Findings by Category

| Category | Description | Count |
|---|---|---|
| **A** | Empty & Near-Empty Files | 5 |
| **C** | Junk / Caches / Build Artifacts | 62 |
| **D** | Potential Orphan Modules | 186 |
| **H** | Exact Hash Duplicates | 3 |

### Top Tier-0 Items (Provable Deletion Candidates if EXECUTE_SAFE were used):
- [`A`] `app/__init__.py`: 0-byte file with no content
- [`A`] `app/notifications/__init__.py`: 0-byte file with no content
- [`A`] `app/py.typed`: 0-byte file with no content
- [`A`] `app/watch/__init__.py`: 0-byte file with no content
- [`A`] `py.typed`: 0-byte file with no content
- [`C`] `.cache/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.cleanup-audit/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.cleanup-audit/.claude/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.coverage`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.hypothesis/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.mypy_cache/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.mypy_cache/.gitignore`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.mypy_cache/3.11/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.mypy_cache/3.12/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.mypy_cache/CACHEDIR.TAG`: Untracked build/dependency/cache artifact directory in workspace
_...and 52 more listed in `manifest.csv`._

## 3. Next Steps & Recommended Actions

1. Review `.purge-reports/manifest.csv` and `.purge-reports/FLAGGED.md`.
2. If safe cleanup is desired, configure `MODE: EXECUTE_SAFE` or generate an approval `PLAN.yaml`.
3. Verify that all untracked artifacts (`__pycache__`, `.venv`, `.pytest_cache`) are properly covered in `.gitignore`.
