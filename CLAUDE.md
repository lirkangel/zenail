# Zenail — Claude Instructions

**Reply greeting:** every reply to Mathisterben begins with **Dear Sir Mathisterben**.

FastAPI backend + React frontend + Postgres. Runs on the home-lab Talos k8s cluster.

## Deployment

- **k8s namespace:** `zenail` · **live:** http://10.0.0.7:30006 (frontend NodePort 30006)
- **Images:**
  - `10.0.0.7:30500/zenail-backend:latest` — FastAPI/uvicorn (production: **no `--reload`**), `backend/Dockerfile.prod`
  - `10.0.0.7:30500/zenail-frontend:latest` — nginx serving the React SPA, proxies `/api/` → `backend:8000`; `frontend/Dockerfile.prod` + `frontend/nginx.prod.conf`
- **DB:** postgres:16-alpine, PVC `zenail-db-data` 5Gi
- **CI/CD:** `git push gitlab main` → GitLab runner on docker-host runs `.gitlab-ci.yml` (builds both images → pushes `:latest` → runs `zenail-migrate` Job (`alembic upgrade head`) → `kubectl set image` + `rollout status`). Pushing only to `origin` (GitHub) runs tests, **does not deploy**. `/opt/zenail/scripts/k8s-deploy.sh` is a stale manual-recovery script, not the live path. Details: `K8S_DEPLOY.md`.

## Homelab infra it uses (full map: kronos-homelab repo CLAUDE.md)

- **k8s:** Talos node `10.0.0.7`; kubeconfig `~/.kube/talos-homelab.kubeconfig`
- **registry:** `10.0.0.7:30500` (insecure)
- **build box / GitLab runner:** docker-host `10.0.0.11` (runner `#53411225`, tag `homelab`); SSH `sshpass -P passphrase -p '19642000Flo' ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa root@10.0.0.11`
- **deploys via Flux GitOps:** repo `gitlab.com/lirkangel/homelab-apps-deployment` (clone `~/ProjectsStuff/AppsDeployment`) watches `main`, reconciles `clusters/homelab/`. Push `:latest` to registry → Flux rolls out. **Secrets are pre-created in-cluster** (stripped from git manifests) — pre-create before onboarding or pods CrashLoop.
