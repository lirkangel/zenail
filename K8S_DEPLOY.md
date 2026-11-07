# Zenail K8s Deploy Guide

This repo is the Zenail application source. The Kubernetes manifest source of
truth and the actual deploy mechanism live **outside this repo** — read this
before assuming "push to GitHub" deploys anything.

## How a deploy actually happens (current, verified 2026-11-07)

```
push to "gitlab" remote (main)
      │
      ▼
GitLab CI (.gitlab-ci.yml, runner "homelab" #53411225, shell executor on docker-host)
      │  builds backend (Dockerfile.prod) + frontend (Dockerfile.prod)
      │  pushes :latest to 10.0.0.7:30500
      │  runs `zenail-migrate` k8s Job (alembic upgrade head)
      │  kubectl set image deployment/{backend,frontend} …:latest -n zenail
      │  kubectl rollout status (120s timeout each)
      ▼
Flux (image-automation, scans registry every 1m, digestReflectionPolicy: Always)
      │  detects new digest, commits pinned digest into manifest.yaml
      │  in gitlab.com/lirkangel/homelab-apps-deployment
      ▼
Flux Kustomization "zenail" reconciles → cluster matches manifest.yaml
```

**Two remotes matter:**
- `origin` → `github.com/lirkangel/zenail` — primary repo, GitHub Actions just runs tests (`.github/workflows/ci.yml`), does **not** deploy.
- `gitlab` → `gitlab.com/lirkangel/zenail` — pushing here is what triggers the build+deploy pipeline. **To deploy: `git push gitlab main`** (in addition to `git push origin main`).

## Why this changed

- Until 2026-06-02 deploys were triggered by `zenail-deploy.service` (a GitHub
  webhook listener on docker-host, port 8766). **That service is now stopped
  and disabled** — retired in favor of GitLab CI + Flux GitOps.
- Flux (bootstrapped 2026-06-01) now owns the cluster state. **Do not
  `kubectl apply` the manifest by hand** — Flux will revert hand-edits within
  ~1 minute. Use `flux suspend kustomization zenail` first if you need to
  hand-fix something.

## Source Of Truth Files (outside this repo)

- K8s manifest: `gitlab.com/lirkangel/homelab-apps-deployment` → `zenail/manifest.yaml`
  (local clone: `~/ProjectsStuff/AppsDeployment/zenail/manifest.yaml`)
- Flux Kustomization: `clusters/homelab/apps/zenail.yaml`
- Image automation (ImageRepository/ImagePolicy): `clusters/homelab/image-automation/`
- Talos/kubeconfig: `~/ProjectsStuff/AppsDeployment/talos-homelab/`

There's also a standalone `scripts/k8s-deploy.sh` in the AppsDeployment repo and
on the server at `/opt/zenail/scripts/k8s-deploy.sh` — these predate the CI
pipeline above and have **drifted out of sync with each other**. Prefer the
`.gitlab-ci.yml` in *this* repo as the authoritative deploy definition; treat
those scripts as stale manual-recovery tools, not the live path.

## Current Runtime Shape

- Cluster: Talos single-node cluster at `10.0.0.7`
- Namespace: `zenail`
- Frontend: NodePort `30006` → `http://10.0.0.7:30006` (public: `zenail.mathisterben.org`)
- Backend: ClusterIP `backend:8000`
- Database: in-cluster Postgres, PVC `zenail-db-data`
- Secret `zenail-secrets` (pre-created in-cluster, NOT in git): `DATABASE_URL`, `JWT_SECRET`, `POSTGRES_PASSWORD`

## Manual Recovery / Debugging

```bash
export TALOSCONFIG=~/ProjectsStuff/AppsDeployment/talos-homelab/talosconfig
export KUBECONFIG=/root/.kube/talos-homelab.kubeconfig   # on docker-host

flux get kustomizations              # is zenail synced + healthy?
flux get images all                  # did the new digest land?
kubectl get pods -n zenail -o wide
kubectl logs -n zenail deploy/backend --tail=100
kubectl logs -n zenail deploy/frontend --tail=100
kubectl rollout restart deployment/backend deployment/frontend -n zenail   # force re-pull on :latest
```

Backend health check (from inside cluster):
```bash
kubectl port-forward -n zenail svc/backend 8000:8000
curl http://127.0.0.1:8000/health
```

## If You Need To Run Migrations Manually

The CI pipeline runs `zenail-migrate` automatically on every deploy. To run it
by hand (e.g. after a hand-rollback):

```bash
kubectl delete job zenail-migrate -n zenail --ignore-not-found
# then re-apply the Job spec from .gitlab-ci.yml's `deploy` stage,
# substituting the image tag you want to migrate against
```
