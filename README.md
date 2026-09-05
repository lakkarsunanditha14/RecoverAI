<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=30&duration=3000&pause=800&color=635BFF&center=true&vCenter=true&width=680&lines=RecoverAI;A+bounded+revenue+recovery+agent;Detect+%E2%86%92+Decide+%E2%86%92+Authorise+%E2%86%92+Execute;It+knows+when+to+stop." alt="RecoverAI" />

### A failed payment is not lost revenue. It is an unfinished decision.

RecoverAI turns failed payments into tracked recovery cases, decides what to do
about each one, acts within limits it cannot exceed, and stops.

<br />

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Postgres](https://img.shields.io/badge/Postgres-Neon-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)

[![Tests](https://img.shields.io/badge/tests-91_passing-15966F?style=flat-square&logo=pytest&logoColor=white)](#testing)
[![Coverage](https://img.shields.io/badge/audit_events-15_types-635BFF?style=flat-square)](#the-audit-trail)
[![Mode](https://img.shields.io/badge/execution-test_simulation-D58A20?style=flat-square)](#test-simulation--read-this-first)
[![Track](https://img.shields.io/badge/Razorpay_Buildathon-Track_3-0C2451?style=flat-square)](#the-brief)

<br />

**[Live dashboard](https://recover-ai-virid.vercel.app)** &nbsp;·&nbsp;
**[API](https://recoverai-3at6.onrender.com/docs)** &nbsp;·&nbsp;
[The loop](#the-recovery-loop) &nbsp;·&nbsp;
[Guardrails](#bounded-automation) &nbsp;·&nbsp;
[Run it](#running-it-locally)

</div>

---

## Test simulation — read this first

> **Recovery execution is simulated. No payment provider is contacted and no
> real money moves.**
>
> `app/simulator/payment_simulator.py` derives each attempt's result
> deterministically from the payment id, the attempt number, and the assessed
> recoverability — so a demonstration replays identically rather than flipping
> between runs. Every simulated result is labelled `test_simulation` in the API
> response, in the audit reason, and in the interface.
>
> The recovery **engine** is real: assessment, decision, policy authorisation,
> execution lifecycle, outcome recording, and audit are ordinary application
> code operating on real database rows. Only the payment provider is simulated.

There is also **no LLM in this system.** The decision layer is deterministic
policy code. That is a deliberate choice, not a missing feature — a recovery
agent that spends money needs behaviour you can test, reproduce, and explain
when it refuses.

---

## The brief

Razorpay Buildathon, **Track 3 — AI Revenue Recovery**. Build an agent that
detects revenue at risk, determines the appropriate intervention, and executes a
bounded recovery workflow.

The word that matters in that brief is **bounded**. Detecting failed payments is
easy. Retrying them is easy. The hard part — and the only part a business would
actually deploy — is an agent that knows when *not* to act, stops when it has
succeeded, gives up when it should, and leaves a record of every decision.

| Requirement | Where it lives |
|---|---|
| Detect revenue at risk | `RiskAssessmentService` — scores from payment state and attempt history |
| Determine intervention | `RecoveryDecisionAgent` — five strategies, selected by recoverability |
| Execute bounded workflow | `RecoveryOrchestratorService` — max 3 attempts, stops on success |
| Measure money recovered | `POST /recovery-batch/run` — totals re-read from the database |
| Compliant escalation | Two distinct paths, both audited |
| Stopping rules | `RecoveryDecisionPolicy.authorize()` — binding, not advisory |
| Audit trail | 15 event types, database timestamps, acting service recorded |

---

## The recovery loop

```mermaid
flowchart TD
    A["💳 Payment at risk"] --> B["📋 Recovery case created"]
    B --> C["📊 Risk assessment<br/><i>risk + recoverability scored</i>"]
    C --> D["🤖 Decision agent<br/><i>recommends a strategy</i>"]
    D --> E{"🛡️ Policy check<br/><b>binding</b>"}

    E -->|refused| F["🚫 Escalate to human<br/><i>0 attempts used</i>"]
    E -->|authorised| G["⚡ Execute attempt"]

    G --> H{"🔍 Verify payment"}
    H -->|succeeded| I["✅ Record outcome<br/>Stop"]
    H -->|failed, attempts left| G
    H -->|failed, limit reached| J["⛔ Retry limit<br/>Escalate to human"]

    I --> K["📜 Audit trail"]
    F --> K
    J --> K

    style E fill:#635BFF,stroke:#4840D4,color:#fff
    style I fill:#15966F,stroke:#0F8A63,color:#fff
    style F fill:#D33F57,stroke:#B03047,color:#fff
    style J fill:#D33F57,stroke:#B03047,color:#fff
    style K fill:#0C2451,stroke:#0C2451,color:#fff
```

The diamond is the whole design. The agent *recommends*; the policy *decides*.
Execution is reachable only through an authorised policy decision.

---

## Bounded automation

A recommendation cannot reach execution unless
`RecoveryDecisionPolicy.authorize()` returns it as authorised. The agent has no
path around it.

| Guardrail | Limit | Behaviour when hit |
|---|---|---|
| **Max retries** | 3 | Stops automation, escalates to a human |
| **Recovery window** | 7 days | Bounds the period a case stays automatable |
| **High risk** | score ≥ 70 | Escalates, executes **nothing** |
| **High value** | ≥ ₹50,000 | Requires policy review before any automation |
| **Already recovered** | — | Stops; never retries a payment that has paid |
| **Closed case** | — | Skipped entirely; duplicate execution blocked |

These values are served live by `GET /recovery-policy` and rendered directly in
the dashboard, so the limits shown to a user cannot drift from the limits
actually enforced.

### Two ways a human gets involved

The audit trail distinguishes them, and so does the interface:

```mermaid
flowchart LR
    subgraph refused ["Refused before execution"]
        A1["risk = 80"] --> A2["policy: escalate"] --> A3["0 of 3 attempts"]
    end
    subgraph exhausted ["Exhausted the ladder"]
        B1["risk = 40"] --> B2["policy: authorise"] --> B3["3 of 3 attempts"] --> B4["all failed"]
    end
    A3 --> C["🙋 Human review"]
    B4 --> C

    style A2 fill:#D33F57,stroke:#B03047,color:#fff
    style B2 fill:#15966F,stroke:#0F8A63,color:#fff
    style C fill:#635BFF,stroke:#4840D4,color:#fff
```

`high_risk_case` means the agent never touched it. `maximum_retry_limit_reached`
means it tried everything it was allowed to. Collapsing those two into one
"escalated" bucket would hide the most interesting thing the system does.

---

## Recovery strategies

The decision layer picks between five actions based on assessed recoverability —
not "retry everything and hope".

| Recoverability | Strategy | Reasoning |
|---|---|---|
| ≥ 80, first attempt | `retry_payment` | A transient failure; retrying is likely to clear it |
| ≥ 60 | `send_reminder` | The customer needs prompting, not another charge attempt |
| ≥ 40 | `update_payment_method` | The instrument itself is the obstacle |
| < 40, or risk ≥ 70 | `escalate` | Below the threshold where automation is appropriate |

`offer_alternative_method` and `manual_review` are also defined in the domain and
available to the action layer.

---

## Architecture

```mermaid
flowchart TB
    UI["⚛️ React 19 + Vite<br/><i>dashboard, agent controls, audit timeline</i>"]
    API["🚀 FastAPI<br/><i>26 routes</i>"]
    ORC["🧠 Recovery Orchestrator<br/><i>the closed loop</i>"]

    subgraph domainlayer ["Decision layer"]
        AG["Decision + Action agents"]
        POL["🛡️ Recovery policy<br/><b>authorisation boundary</b>"]
    end

    subgraph servicelayer ["Services"]
        RISK["Risk assessment"]
        EXEC["Action execution"]
        OUT["Outcome recording"]
        AUD["Audit events"]
    end

    REPO["📚 Repositories"]
    DB[("🗄️ PostgreSQL<br/>Neon · 15 migrations")]
    SIM["🧪 Payment simulator<br/><i>test simulation</i>"]

    UI -->|HTTP/JSON| API
    API --> ORC
    ORC --> AG --> POL
    POL -->|authorised only| EXEC
    ORC --> RISK & OUT & AUD
    EXEC --> SIM
    RISK & EXEC & OUT & AUD --> REPO --> DB

    style POL fill:#635BFF,stroke:#4840D4,color:#fff
    style ORC fill:#0C2451,stroke:#0C2451,color:#fff
    style SIM fill:#D58A20,stroke:#B8761A,color:#fff
```

Layered deliberately: API handlers stay thin, services hold the workflow,
repositories own persistence, and the domain has no framework imports at all.

```text
app/
├── agents/        decision and action agents
├── api/           FastAPI routers — thin, no business logic
├── core/          database engine and session
├── domain/        9 dataclasses + enums, zero framework dependencies
├── models/        SQLAlchemy ORM mappings
├── policies/      the authorisation boundary
├── repositories/  persistence, one per aggregate
├── services/      workflow, including the orchestrator
└── simulator/     seed data, reset, payment simulation
```

---

## The audit trail

Fifteen event types, written by the service that acted, timestamped by the
database. A completed recovery reads as a chronology:

```text
 1  risk_assessed         risk_assessment_service     Risk 0, recoverability 100
 2  policy_checked        recovery_decision_policy    factors: risk=0 retry=0/3
 3  decision_generated    recovery_decision_agent     recommended retry_payment
 4  action_authorized     recovery_decision_policy    attempt 1/3 authorised
 5  action_executed       recovery_action_service     approved → started → done
 6  payment_verified      payment_simulator           TEST SIMULATION: succeeded
 7  outcome_recorded      recovery_outcome_service     4999.00 recovered
 8  recovery_completed    recovery_outcome_service     4999.00 of 4999.00
 9  case_stopped          orchestrator                 automation stopped
```

A refused case is three events and stops at the policy. An exhausted case runs to
eleven and ends in `retry_limit_reached` → `case_escalated`. Nothing is
fabricated in the frontend; every timestamp is the one stored in Postgres.

<details>
<summary><b>All 15 event types</b></summary>

<br />

| Event | Written by |
|---|---|
| `payment_received` / `payment_failed` | payment lifecycle |
| `risk_assessed` | `RiskAssessmentService` |
| `decision_generated` | orchestrator, after the agent |
| `policy_checked` | `RecoveryDecisionPolicy` |
| `action_proposed` | `RecoveryActionService` |
| `action_authorized` | policy, before execution |
| `action_executed` | `RecoveryActionExecutionService` |
| `payment_verified` | payment simulator |
| `retry_attempted` | orchestrator, between attempts |
| `retry_limit_reached` | orchestrator, on exhaustion |
| `outcome_recorded` | `RecoveryOutcomeService` |
| `recovery_completed` | on a successful or partial recovery |
| `case_escalated` | either escalation path |
| `case_stopped` | on any terminal stop |

</details>

---

## Measured recovery

`POST /recovery-batch/run` processes open cases through the same orchestrator a
single case uses — there is no separate "demo mode" that produces nicer numbers.

Every figure it returns is **re-read from the database after the run**, never
accumulated by the endpoint while looping:

```json
{
  "cases_processed": 3,
  "cases_remaining": 25,
  "total_revenue_at_risk": 438942.0,
  "revenue_recovered": 88645.0,
  "remaining_revenue_at_risk": 350297.0,
  "recovery_rate": 20.2,
  "recovered_cases": 17,
  "escalated_cases": 11,
  "mode": "test_simulation"
}
```

Two identities must always hold, and there are tests asserting both:

```text
revenue_recovered + remaining_revenue_at_risk == total_revenue_at_risk
recovered + failed + escalated + stopped + active == total cases
```

Recovered revenue is summed from **recovery outcomes**, so a partial recovery
contributes the amount that actually came back rather than the full amount at
risk — a distinction that quietly inflates most recovery dashboards.

---

## API

<details open>
<summary><b>The agent</b></summary>

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/recovery-cases/{case_id}/run` | Run the full loop for one case |
| `POST` | `/recovery-batch/run?limit=N` | Run a bounded slice of open cases |
| `GET` | `/recovery-policy` | The guardrails actually enforced |

</details>

<details>
<summary><b>Cases, assessment, decisions</b></summary>

| Method | Route |
|---|---|
| `GET` | `/recovery-cases` |
| `POST` | `/recovery-cases/{payment_id}` |
| `GET` | `/recovery-cases/{case_id}` |
| `POST` | `/recovery-cases/{case_id}/risk-assessments` |
| `POST` | `/recovery-cases/{case_id}/decisions` · `/decisions/ai` |

</details>

<details>
<summary><b>Actions, outcomes, audit</b></summary>

| Method | Route |
|---|---|
| `POST` | `/recovery-cases/{case_id}/actions` · `/ai-action` |
| `POST` | `/recovery-actions/{action_id}/approve` · `start` · `complete` · `fail` |
| `GET` `POST` | `/recovery-cases/{case_id}/outcomes` |
| `GET` `POST` | `/recovery-cases/{case_id}/audit-events` |
| `GET` | `/audit-events?limit=N` |

> These individual endpoints exist for manual operation and debugging. They are
> **operator tools and are not policy-gated** — the bounded guarantees described
> above apply to the orchestrated path (`/run` and `/recovery-batch/run`), which
> is what the interface uses.

</details>

---

## Running it locally

**Requires** Python 3.12+, Node 22+, and a PostgreSQL connection string.

```bash
git clone https://github.com/lakkarsunanditha14/RecoverAI.git
cd RecoverAI

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then set DATABASE_URL
alembic upgrade head
```

> **`DATABASE_URL` must use the psycopg 3 prefix.** Neon hands you
> `postgresql://…`, which SQLAlchemy resolves to psycopg **2** and fails on:
>
> ```text
> postgresql+psycopg://user:pass@host/db?sslmode=require
> ```

Seed the demo batch and start the API:

```bash
python -m app.simulator.seed          # 23 payments across every scenario
python -m app.simulator.reset_cases   # clean, repeatable starting state
uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

---

## Try the agent

The seeded batch is engineered so each scenario is reachable and reproducible.

| Try this | Payment | What happens |
|---|---|---|
| 🟢 **Clean recovery** | `pay_2004` | Recovers on attempt 1 · `payment_recovered` |
| 🟡 **Retry ladder** | `pay_2001` | Fails, retries, recovers on a later attempt |
| 🔴 **Exhausted** | `pay_2014` | 3 of 3 attempts fail · `maximum_retry_limit_reached` · escalated |
| 🛑 **Refused** | `pay_2011` | **0 attempts** · `high_risk_case` · policy blocked it |
| 💰 **High value** | `pay_2020` | ₹75,000 · `high_value_requires_policy_review` |

```bash
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
for pid in ['pay_2004','pay_2014','pay_2011']:
    cid = next(x['case_id'] for x in c.get('/recovery-cases').json() if x['payment_id']==pid)
    r = c.post(f'/recovery-cases/{cid}/run').json()
    print(f\"{pid}: {r['status']:10} {r['attempt_number']}/3  {r['stop_reason']}\")
"
```

Compare `pay_2011` and `pay_2014`. Both escalate to a human. One used every
attempt it had; the other was never allowed to start. That difference is the
entire argument for bounded automation.

---

## Testing

```bash
python -m pytest -q                    # 91 tests
python -m pytest tests/unit -q         # 67, no database, ~2s
python -m pytest tests/integration -q  # 24, hits the database
python -m app.simulator.reset_cases    # reset afterwards
```

```text
91 passed
```

The suite covers the strategy table, every guardrail in `authorize()`, the
simulator's determinism, the retry ladder at each attempt, stop-on-success,
duplicate-execution blocking, audit event ordering, and the batch metric
identities.

One test exists purely to fail loudly if the strategy table ever regresses to
returning `retry_payment` for everything — the failure mode this system is
designed to avoid.

> Integration tests write to the configured database. Run
> `python -m app.simulator.reset_cases` afterwards before demonstrating.

---

## Known limits

Stated plainly, because a submission that hides its edges is worse than one that
names them.

| Limit | Detail |
|---|---|
| **Batch latency** | A full retry ladder costs ~40 commits. Against a remote database that is seconds per case; the endpoint is chunked via `?limit=N` so no single request times out. The real fix is one transaction per case. |
| **Manual endpoints are ungated** | The lifecycle routes bypass `authorize()` by design, as operator tools. Only the orchestrated path is bounded. |
| **No partial recovery from automation** | The orchestrator records `recovered` or `not_recovered`. Partial outcomes are reachable through the manual outcome flow. |
| **Simulated execution** | No payment provider integration. See the notice at the top. |
| **No authentication** | Every endpoint is open. This is a prototype, not a deployed product. |

---

## Roadmap

- One transaction per case, cutting batch latency by an order of magnitude
- Policy authorisation on the manual endpoints, closing the operator gap
- Live payment-provider integration behind the existing simulator interface
- Partial recovery as a first-class orchestrated outcome
- Recovery-window enforcement against case age
- Historical performance: which strategy actually recovers most, by segment

---

<div align="center">

### Built for the Razorpay Buildathon — Track 3

**Lakkarsu Nanditha**

*Don't just detect failed payments. Decide what to do, act within limits you
cannot exceed, measure what came back, and keep the receipts.*

<br />

[![Dashboard](https://img.shields.io/badge/Live_Dashboard-635BFF?style=for-the-badge&logo=vercel&logoColor=white)](https://recover-ai-virid.vercel.app)
[![API Docs](https://img.shields.io/badge/API_Docs-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://recoverai-3at6.onrender.com/docs)

</div>
