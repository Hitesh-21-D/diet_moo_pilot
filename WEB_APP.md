# AmritAHARA local research application

AmritAHARA connects the existing six optimizers to accounts, personal profiles,
multi-day food diaries, recommendations and a separate research analysis page.
It runs entirely on your Windows computer. Docker is not required.

For terminal-only questionnaire imports and multi-participant benchmarking, see
[the survey batch guide](docs/SURVEY_BENCHMARK.md). It supports all six algorithms,
aggregate metrics, resumable jobs and incremental imports without starting the app.

## Start and stop

From PowerShell in this project:

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-AmritAHARA.ps1
```

Open **http://127.0.0.1:8000** and choose **Create an account**. Save your body
statistics in **My profile**, record one or more days in **Diet diary**, save
the diary, select the days and start computation. The default budget is 15,000
evaluations. Select the six algorithms to create a comparative experiment.

Each selected input day receives a separate experiment and recommendation set.
Switch between them with the input-day selector. A feasible run provides three
representative choices; if the search finds no feasible diet, the app says so
and does not invent an output. Input foods come from all 818 audited usable INDB records. Every meal can use
the full catalogue. Custom foods outside the workbook and allergy filtering are
not implemented. See `docs/FLEXIBLE_FORMULATION.md` for the data audit and rules.

The launcher starts native PostgreSQL, the API and the worker in hidden
background processes. Existing services are reused. There is no Windows
service installation and no administrator requirement. It binds to loopback
only; this is a local research application, not a public deployment.

To stop:

```powershell
powershell -ExecutionPolicy Bypass -File .\Stop-AmritAHARA.ps1
```

Queued jobs survive a restart. Interrupted running jobs are marked failed
after the stale heartbeat timeout (two minutes); start a new experiment to
retry. Saved completed results survive restart. Do not edit scientific source
files while jobs are queued: source/dataset fingerprints are checked before
each run, and changed inputs require a new experiment.

## Free technology stack

| Layer | Tools |
| --- | --- |
| Interface | React 19, TypeScript 5.7, Vite 6, React Router 7 |
| Forms and data | React Hook Form 7, Zod 4, TanStack Query 5 |
| Charts and icons | Plotly.js 3, Lucide React; no hosted chart service |
| Styling | Local CSS and CSS Modules, system fonts, solid colours |
| API | Python 3.12, FastAPI, Uvicorn, Pydantic |
| Database | Native PostgreSQL 17, SQLAlchemy, psycopg, Alembic |
| Authentication | Argon2 password hashes, random opaque sessions, HttpOnly cookies |
| Computation | Existing NumPy, pandas, SciPy, pymoo implementations; isolated Python subprocesses |
| Job queue | PostgreSQL rows claimed with `FOR UPDATE SKIP LOCKED`; one sequential worker |
| Verification | pytest, FastAPI TestClient/httpx, Vitest, React Testing Library, browser checks |

No paid API, cloud account, email provider, Redis or Docker dependency is used.
Package versions are recorded in `requirements-web.lock.txt` and
`frontend/package-lock.json`. Electricity/storage and any future public
hosting are separate from these free software tools.

## Research interpretation

- Every experiment freezes the profile, targets, original diet, requested
  budget, seeds and source/dataset SHA-256 fingerprints.
- New runs use flexible-v2: four objectives and nine nutrient constraints plus
  four checks per named meal. Every returned diet is independently validated.
  Historical pilot results retain their original 24-variable/33-constraint snapshots.
  Do not combine pilot and flexible-v2 results in a benchmark.
- APPO uses the exact evaluation budget including repair trials. Baselines
  use whole generations at or below the requested budget (MOEA/D population
  84). The UI reports the actual evaluation counts.
- A completed multi-algorithm cohort shares one nondominated reference front
  and normalization across all included algorithms and seeds for that day.
  HV, IGD, spacing and PETQ are frozen only when the cohort is complete.
  These values cannot be compared numerically across different experiments.
- Single-algorithm runs show direct diagnostics and diets, but do not report
  self-referential comparative HV/IGD/PETQ. Failed/cancelled cohorts are marked
  incomplete rather than silently dropping algorithms.
- Population feasibility and evaluated-candidate feasibility are different.
  The latter is observed in 100-evaluation windows. APPO's recorded population,
  archive and adaptive operator histories are shown separately; unavailable
  baseline generation histories are explicitly identified.
- Search runtime includes the instrumentation/database checkpoint overhead.
  It is suitable for diagnosing this app, not directly interchangeable with
  the uninstrumented CLI benchmark timings.
- Repeated-seed comparisons include mean/SD, paired Wilcoxon tests, Holm
  correction and rank-biserial effects. At least three valid pairs are needed
  for a p-value in the existing statistics routine. A one-seed app check is
  functional validation, not proof of APPO's superiority.
- JSON experiment exports include snapshots, all runs, diagnostics, full
  solution archives and metrics. Diet CSV and comparative metrics CSV are
  available separately. Print uses the browser's print/PDF capability.

## Data and authentication

PostgreSQL data lives in `.local/pgdata`; its generated local connection
secret lives in `.local/app-settings.json`. Logs are in `.local/logs`.
These paths are git-ignored. Do not publish that directory. To make a simple
local backup, stop the app cleanly and copy `.local/pgdata` together with
`.local/app-settings.json` to a private backup location. Use the same
PostgreSQL major version when restoring a data-directory backup.

Accounts are local: no email verification, password-recovery email or social
login. Sessions last seven days. Ownership is enforced by the API for reads,
exports and cancellation. Write requests require an application header and
same-origin checks. Login throttling is per process. Public deployment would
need HTTPS, deployment-specific origins, secure cookies, operational backups
and a separate security review.

The verification script creates a clearly labelled validation account with
a known test password and the existing pilot inputs. Keep your own records
in your own new account. This validation account contains no real new-user
data and is not intended for personal use.

## Installation on another Windows computer

Use Python 3.12 and Node.js 20.19 or later supported by Vite 6. Create a venv,
install the pinned Python dependencies, install the frontend dependencies and
build:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-web.lock.txt
cd frontend
npm ci
npm run build
cd ..
```

Download the Windows x64 PostgreSQL binaries from the official
[PostgreSQL Windows download page](https://www.postgresql.org/download/windows/)
or its linked EDB binaries page. The tested archive is
`postgresql-17.11-3-windows-x64-binaries.zip`. Save it as
`.local/downloads/postgresql.zip`, then run `Start-AmritAHARA.ps1`. The native
setup script extracts the required binaries, initializes SCRAM authentication,
creates the database on port 5433 and runs migrations. No Docker is involved.
The original project dataset must also be present.

For development, run the API and worker as above, then `npm run dev` inside
`frontend`. Vite serves port 5173 and proxies `/api` to port 8000. Production
local use serves the built frontend directly from FastAPI on port 8000.

## Verification commands

```powershell
.venv\Scripts\python.exe -B -m pytest tests_web -q
cd frontend
npm test
npm run build
cd ..
.venv\Scripts\python.exe -u -B scripts/verify_web_pipeline.py
```

The last command requires the running app. It creates two distinct input
days, runs six full-budget algorithms on the first and APPO on the second,
checks constraints and exports, and saves `.local/web-verification.json`.
Use `--resume` to check the already-created validation experiments after a
terminal interruption. It does not reset other users' records. Unit API tests
use a temporary SQLite database; application/integration tests use PostgreSQL.

The frontend chart bundle is lazy-loaded and relatively large. Build warnings
about its chunk size are expected; no chart library is fetched from a CDN at
runtime. Browser access after installation does not require internet.
