# Skill: Deploy to Railway

## Trigger
Auto-invoke when the user asks to "deploy", "push to production", "ship it", or "go live".

## Pre-Deploy Checklist
1. Run TypeScript compilation check: `cd frontend && npx tsc -b --noEmit`
   - If type errors exist, fix them BEFORE deploying (Railway will fail)
2. Run a local test audit: `/project:test-audit`
3. Check for uncommitted changes: `git status`
4. Verify Dockerfile builds locally: `docker build -t waio-test .`

## Deploy Steps
1. Stage all changes: `git add -A`
2. Commit with descriptive message: `git commit -m "feat: [description of changes]"`
3. Push to main: `git push origin main`
4. Railway auto-deploys from main branch
5. Monitor deploy at Railway dashboard
6. After deploy, verify health: `curl https://waio.up.railway.app/api/health`

## Post-Deploy Verification
1. Check health endpoint returns `{"status": "ok"}`
2. Run a quick audit through the live UI
3. Verify PDF export still works
4. If errors, check Railway deploy logs

## Rollback
If deploy fails: `git revert HEAD && git push origin main`
