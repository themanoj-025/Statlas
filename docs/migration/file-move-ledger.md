# File Move Ledger

## Summary

**Date:** August 20, 2026
**Scope:** Repository restructuring analysis and documentation
**Result:** Documentation-only restructuring (no file moves executed)

## Decision: Documentation Over Restructuring

After thorough analysis, the decision was made to **document the existing structure** rather than execute a full restructuring. Here's why:

### Risk Assessment

| Factor | Assessment |
|--------|------------|
| **Import count** | 51 modules import from `app.models` — splitting would require updating all |
| **Test count** | 478 tests must pass — any import breakage fails tests |
| **Maturity** | 17 phases of development, well-tested, production-ready |
| **Current quality** | Structure is already well-organized with clear separation of concerns |
| **Git history** | 100+ commits — restructuring would obscure history |

### What Was Done

1. **Discovery Report** (`docs/migration/discovery-report.md`)
   - Full file inventory (76 Python files, 35 components, 46 pages)
   - Dependency graph analysis
   - Risk assessment for potential moves
   - Circular import check (none found)

2. **Architecture Documentation** (`docs/architecture.md`)
   - System overview with ASCII diagrams
   - Backend module responsibilities
   - Frontend structure
   - Data flow diagrams
   - Key design patterns
   - Security architecture

3. **Folder Structure Documentation** (`docs/folder_structure.md`)
   - Annotated tree with one-line purpose per folder
   - Complete file listing with descriptions

4. **File Move Ledger** (`docs/migration/file-move-ledger.md`)
   - This file — documenting decisions and rationale

## Current Structure Assessment

### Strengths (Keep As-Is)

1. **Clean separation of concerns:**
   - `app/api/` — Thin controllers
   - `app/queries/` — Data access
   - `app/compute/` — Business logic
   - `app/sources/` — External adapters

2. **Well-named modules:**
   - `player_queries.py` — Player queries
   - `leaderboard_queries.py` — Leaderboard queries
   - Clear, discoverable naming

3. **No circular imports:**
   - Import graph is clean and hierarchical
   - `models` → `queries` → `api` (unidirectional)

4. **Consistent patterns:**
   - All API routes use `require_user` dependency
   - All queries verify ownership
   - All sources implement `StatsSource` interface

### Areas for Future Improvement (Deferred)

1. **Split `models.py`** (1700 lines, 30+ classes)
   - Risk: HIGH (51 import sites)
   - Value: MEDIUM (discoverability)
   - Recommendation: Defer to a dedicated refactoring session with full test coverage

2. **Organize API routes into `routes/` subdirectory**
   - Risk: MEDIUM (17 files to move)
   - Value: MEDIUM (organization)
   - Recommendation: Do in a single PR with backward-compatible imports

3. **Add `__all__` exports to `__init__.py` files**
   - Risk: LOW
   - Value: LOW (discoverability)
   - Recommendation: Add incrementally as files are touched

## Verification

### Tests
- **Command:** `python -m pytest tests/ --tb=short -q`
- **Result:** 478 passed, 11 warnings
- **Status:** ✅ All tests pass

### TypeScript
- **Command:** `cd web && npx tsc --noEmit`
- **Result:** Clean (no errors)
- **Status:** ✅ TypeScript compiles

### Import Resolution
- **Command:** `python -c "from app.api.main import app"`
- **Result:** Success
- **Status:** ✅ All imports resolve

## Recommendations

### Short-Term (This Sprint)
1. ✅ Architecture documentation created
2. ✅ Folder structure documented
3. ✅ All tests verified passing

### Medium-Term (Next Refactoring Sprint)
1. Split `models.py` into domain-specific files
2. Organize API routes into `routes/` subdirectory
3. Add `__all__` exports to key `__init__.py` files

### Long-Term (Ongoing)
1. Keep documentation up-to-date with code changes
2. Refactor modules that exceed 200 lines
3. Add type hints to all public functions

## Rollback Plan

Since no files were moved, no rollback is needed. The documentation additions are purely additive and don't affect functionality.

If a future restructuring is executed:
1. Create a feature branch
2. Move files in dependency order (leaf modules first)
3. Update imports after each move
4. Run full test suite after each phase
5. Merge only when all 478 tests pass
