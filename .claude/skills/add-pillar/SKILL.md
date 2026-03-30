# Skill: Add Audit Pillar

## Trigger
Auto-invoke when the user asks to "add a new pillar", "create a new audit module", "add [topic] analysis", or "implement the [name] auditor".

## Workflow

### Phase 1: Understand
1. Identify the pillar name, label, and purpose from the user's request
2. Check `.claude/rules/sprint-plan.md` to see if this pillar is already planned
3. Determine the appropriate weight (premium pillars may not affect free tier scoring)

### Phase 2: Create Backend Module
1. Read `.claude/rules/auditor-interface.md` for the contract
2. Create `backend/{name}_auditor.py` with:
   - Main `run_{name}_audit()` function
   - Individual check functions
   - `create_finding()` helper
   - Proper type hints and docstring
3. Each check must have pass/fail states with `positive_message` for passes

### Phase 3: Integrate
Follow the EXACT checklist in `.claude/rules/auditor-interface.md` → Integration Checklist.
This includes: main.py, scoring.py, report_generator.py, AuditReport.tsx pillarMeta, LoadingState.tsx, pdf_generator.py, md_generator.py, site_crawler.py, competitive_auditor.py.

### Phase 4: Test
Run `/project:test-audit` to verify the new pillar appears in results.

### Phase 5: Report
Show the user:
- New files created
- Files modified
- New scoring weights (must sum to 1.0)
- Sample finding output from the new pillar
