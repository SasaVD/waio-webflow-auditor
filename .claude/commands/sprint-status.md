# /project:sprint-status

Check the current implementation progress against the sprint plan.

1. Read `.claude/rules/sprint-plan.md` for the full plan
2. Scan the backend/ directory for new files that correspond to sprint deliverables
3. Check `requirements.txt` for new dependencies (asyncpg, scikit-learn, d3, etc.)
4. Check `main.py` for new endpoints
5. Check the database schema (db.py or db_postgres.py) for new tables
6. Report:
   - Which sprint items are DONE (file exists, integrated)
   - Which are IN PROGRESS (file exists, not fully integrated)
   - Which are NOT STARTED
   - What should be worked on next
