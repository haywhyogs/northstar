# Testing and the delivery pipeline: from the fundamentals up

> Reference note. We'll build each piece on Days 2 and 5, and come back to this page to check understanding.

## 1. The big idea: catch problems early, when they're cheap
Think of a **car factory**:
- Each part is inspected before assembly → **unit tests**
- The engine is tested once it's assembled → **integration tests**
- Suppliers' parts are checked against recall lists → **dependency scanning**
- The finished car gets a safety inspection → **container image scanning**
- Someone takes it round the block after delivery → **smoke test**
- A manager signs it off before it goes to the showroom → **manual approval**

The earlier a check runs, the cheaper the fix. Industry calls this **"shift left"** (moving checks earlier in the timeline).

## 2. Every check, one by one

| # | Check | The question it answers | Example in Northstar | Tool | Runs when |
|---|---|---|---|---|---|
| 1 | **Formatting and linting** | Is the code tidy, with no obvious mistakes? | Unused variable, bad indentation | `ruff` (Python), `eslint` (TS), `terraform fmt` | Every PR |
| 2 | **Unit tests** | Does each small piece of logic work **on its own**? | "Transfer bigger than the balance is rejected" | `pytest` | Every PR (seconds, no database) |
| 3 | **Integration tests** | Do the pieces work **together with real dependencies**? | API + a real SQL Server container: debit and outbox saved together; **duplicate message ≠ duplicate credit** | `pytest` + service containers | Every PR |
| 4 | **Terraform validate and plan** | Is the infrastructure code valid, and **what exactly would change in Azure**? | "Plan: 3 to add, 0 to change, 0 to destroy" | `terraform` | PRs touching `infrastructure/` |
| 5 | **IaC security scan** | Is our infrastructure configured insecurely? | Storage account allowing public blob access | Trivy (config mode) | Every PR |
| 6 | **Dependency scan (SCA)** | Do the **libraries we import** have known vulnerabilities (CVEs)? | An old FastAPI version with a published CVE | `pip-audit`, `npm audit`, Trivy (fs mode), Dependabot | Every PR + weekly |
| 7 | **Secret scanning** | Did anyone commit a password, key or token? | An Azure key pasted into a config file | `gitleaks` in CI + GitHub secret scanning and push protection | Every push |
| 8 | **Container image scan** | Does the **finished image** (OS packages + libraries) contain known vulnerabilities? | A vulnerable `openssl` in the Debian base image | Trivy (image mode) | After build, **before** push/deploy |
| 9 | **Smoke tests** | Is the **deployed** app alive and doing its most basic job, in a **real environment**? | `/healthz` returns 200; a test payment reaches `completed` | `pytest`/`curl` against the dev URL | After **every** deployment; failure blocks promotion |
| 10 | **Manual approval** | Does a responsible human agree to release this? | Reviewer account approves the `staging` deployment | GitHub environment protection | Before staging |
| 11 | **Kubernetes probes** (runtime, not CI) | Is this container healthy **right now**? | Readiness: "don't send me traffic yet"; liveness: "restart me, I'm stuck" | Kubernetes | Continuously |

### The pairs people mix up
- **Unit vs integration:** unit tests a piece **in isolation** (fast, fake surroundings). Integration tests pieces **with real neighbours** (a real database, a real queue emulator).
- **Integration vs smoke:** integration tests run **in CI before deployment**, on throwaway containers. Smoke tests run **after deployment**, against the **real environment**. They're shallow, but prove the real thing works (identity, network, DNS, config).
- **Dependency scan vs image scan:** a dependency scan checks **our libraries** (from `pyproject.toml`/`package.json`). An image scan checks **everything in the box**, including OS packages from the base image that we never chose explicitly.
- **Vulnerability scanning vs secret scanning:** a vulnerability scan asks "is this software known to be weak?" A secret scan asks "did **we** leak a credential?"
- **Tests vs approvals:** tests are automated evidence. An approval is a **human decision** recorded in GitHub with a name and a timestamp.

### What we deliberately won't do (and can say why in an interview)
Load or performance tests (stretch goal), full browser end-to-end tests, penetration testing. They're valuable, but not in a 7-day, $10 scope.

## 3. How the checks are arranged: the pipeline

```
PULL REQUEST (is this change safe to merge?)
 ├─ job: backend lint + unit + integration ─┐
 ├─ job: web lint + build                   │
 ├─ job: terraform fmt + validate + plan    │  all run IN PARALLEL
 ├─ job: dependency + IaC scan              │
 ├─ job: secret scan                        │
 └─ job: image build + image scan (no push) ┘
        all green ✅ + reviewer approval ✅ → merge allowed

MERGE TO MAIN (ship it)
 build image ONCE (tag = commit SHA) → image scan → push to ACR
   → deploy to *-dev → smoke tests
   → ⏸ manual approval (reviewer account)
   → deploy the SAME image to *-staging → smoke tests
```

### Why parallel?
In GitHub Actions, **jobs in a workflow run in parallel by default**. You add `needs:` only when a job truly depends on another.
Six 2-minute checks one after another take about 12 minutes. In parallel they take about 2–3 minutes, roughly the length of the longest job.
**Rule of thumb:** only put things in sequence when one needs the other's output (you can't scan an image before it's built,
or deploy to staging before dev is proven).

### Why "build once, deploy many"?
The image tested in dev must be **byte-for-byte the same** as the one in staging. If we rebuilt for staging,
a library could quietly update in between. The **commit SHA tag** (e.g. `payments-api:3f9c2ab`) ties every running container
back to the exact code that produced it. `latest` changes meaning every build, so it can't tell you what's running.

## 4. Caching: why the second build is much faster

### a) Dependency caching
Installing 100+ Python/Node packages on every run is slow. CI saves the package download cache (uv's cache, npm's cache)
and restores it on the next run, keyed on the **lockfile**. When the lockfile changes, the cache is rebuilt.

### b) Docker layer caching
An image is built in **layers**: each Dockerfile instruction is one layer. If a layer's inputs haven't changed, Docker reuses it.
**Order matters:** put things that rarely change first.

```dockerfile
# Stage 1: build (has compilers and build tools)
FROM python:3.12-slim AS build
COPY pyproject.toml uv.lock ./        # ① changes rarely
RUN uv sync --frozen --no-dev         # ② slow, but CACHED if ① didn't change
COPY src/ ./src/                      # ③ changes often; only this and later layers rebuild

# Stage 2: runtime (only what's needed to RUN: smaller, fewer vulnerabilities)
FROM python:3.12-slim
COPY --from=build /app /app
USER 10001                            # non-root
```

Edit one `.py` file → only layer ③ rebuilds, in seconds. Edit `uv.lock` → ② and ③ rebuild.
GitHub-hosted runners start empty each time, so **BuildKit** stores layers in GitHub's cache between runs
(`cache-from: type=gha`, `cache-to: type=gha,mode=max`).

### c) Multi-stage builds
The build stage has compilers and tools; the runtime stage copies only the results.
This gives a smaller image, a faster pull and **fewer packages for attackers or scanners to worry about**.
_(The snippet above is illustrative. The real Dockerfile also installs the ODBC driver and is written on Day 2.)_

## 5. Official references
- GitHub Actions jobs and `needs`: https://docs.github.com/actions/writing-workflows/choosing-what-your-workflow-does/using-jobs-in-a-workflow
- GitHub deployment environments and approvals: https://docs.github.com/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
- GitHub secret scanning: https://docs.github.com/code-security/secret-scanning/introduction/about-secret-scanning
- Docker build cache: https://docs.docker.com/build/cache/
- Docker GitHub Actions cache backend: https://docs.docker.com/build/cache/backends/gha/
- Docker multi-stage builds: https://docs.docker.com/build/building/multi-stage/
- Trivy: https://trivy.dev/
- Kubernetes probes: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/

## 🧠 Check yourself (answer in your own words)
1. A smoke test fails in dev, but all PR tests passed. Name two things that could be wrong that the PR tests couldn't see.
   > **My answer (2026-11-12):** The smoke test checks for vulnerabilities in the built image before it moves on; maybe a dependency or Python version changed.
   >
   > **Correction:** a smoke test doesn't look for vulnerabilities; that's the **image scan**. A smoke test asks
   > "does the deployed app actually work **in this real environment**?" Because the same pinned image passed CI, the cause is
   > usually something **only the environment has**:
   > - **Identity:** the pod's workload identity wasn't granted access to SQL, so login fails
   > - **Networking/DNS:** the pod can't resolve the SQL private endpoint
   > - **Configuration:** a wrong ConfigMap value, or a missing secret in Key Vault
   > - **Deployment:** AKS can't pull the image from ACR (missing `AcrPull`), or migrations weren't run
2. Why does the image scan sometimes find vulnerabilities that the dependency scan didn't?
   > **My answer:** The dependency scan only checks the dependencies; the image scan checks everything, including Dockerfile changes.
   >
   > **Correction (partly right ✅):** "the image scan checks everything" is the key idea. More precisely: the dependency scan reads
   > **our** library list (`pyproject.toml`/`uv.lock`, `package.json`: FastAPI, SQLAlchemy…). The image scan looks **inside the finished box**:
   > the base image's **operating-system packages** (Debian's `openssl`, `glibc`), the **Python interpreter** itself, and anything the
   > Dockerfile installs (e.g. the ODBC driver). We never listed those in a dependency file, so the dependency scan can't see them.
3. Why do we promote the same image SHA to staging instead of rebuilding?
   > **My answer:** Consistency. Rebuilding could pick up dependency updates, and doing it continuously creates drift.
   >
   > **✅ Correct.** One addition: it also gives **traceability**. The SHA tag proves *exactly* which code is running, and that it's the thing that was tested.
