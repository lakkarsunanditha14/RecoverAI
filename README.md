<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=30&duration=3000&pause=800&color=635BFF&center=true&vCenter=true&width=680&lines=RecoverAI;A+bounded+revenue+recovery+agent;Diagnose+%E2%86%92+Decide+%E2%86%92+Authorise+%E2%86%92+Execute;It+knows+when+to+stop." alt="RecoverAI" />

# RecoverAI

### AI-Powered Closed-Loop Revenue Recovery and Intelligent Payment Intervention Engine

<br />

**A failed payment is not lost revenue. It is an unfinished decision.**

RecoverAI turns failed payments into tracked recovery cases, works out *why*
each one failed, decides what to do about it, acts within limits it cannot
exceed, and stops.

<br />

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Postgres](https://img.shields.io/badge/Postgres-Neon-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)

[![Tests](https://img.shields.io/badge/tests-111_of_113_passing-15966F?style=flat-square&logo=pytest&logoColor=white)](#testing)
[![Audit](https://img.shields.io/badge/audit_events-16_types-635BFF?style=flat-square)](#the-audit-trail)
[![Webhook](https://img.shields.io/badge/razorpay-live_webhook_ingestion-0C2451?style=flat-square)](#live-webhook-ingestion)
[![Mode](https://img.shields.io/badge/execution-test_simulation-D58A20?style=flat-square)](#test-simulation--read-this-first)
[![Track](https://img.shields.io/badge/Razorpay_Buildathon-Track_3-0C2451?style=flat-square)](#the-brief)

<br />

**[Live dashboard](https://recover-ai-virid.vercel.app)** &nbsp;·&nbsp;
**[API](https://recoverai-3at6.onrender.com/docs)** &nbsp;·&nbsp;
[The loop](#the-recovery-loop) &nbsp;·&nbsp;
[Diagnosis](#failure-diagnosis) &nbsp;·&nbsp;
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
> The recovery **engine** is real: ingestion, diagnosis, assessment, decision,
> policy authorisation, execution lifecycle, outcome recording, and audit are
> ordinary application code operating on real database rows. Only the payment
> provider is simulated.

**Webhook ingestion is not simulated.** `POST /webhooks/razorpay` accepts a real
Razorpay `payment.failed` payload, writes the customer, payment, and recovery
case to Postgres, and records the audit event. That path touches the same tables
as everything else.

There is also **no LLM in this system.** The diagnosis and decision layers are
deterministic code. That is a deliberate choice, not a missing feature — a
recovery agent that spends money needs behaviour you can test, reproduce, and
explain when it refuses.

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
| Ingest live failures | `POST /webhooks/razorpay` — real payload, real rows |
| Diagnose the cause | `PaymentDiagnosisService` — 7 categories, deterministic |
| Detect revenue at risk | `RiskAssessmentService` — scores from payment state and attempt history |
| Determine intervention | `RecoveryDecisionPolicy.recommend()` — diagnosis first, score as fallback |
| Execute bounded workflow | `RecoveryOrchestratorService` — max 3 attempts, stops on success |
| Measure money recovered | `GET /recovery-metrics` — totals re-read from the database |
| Compliant escalation | Two distinct paths, both audited |
| Stopping rules | `RecoveryDecisionPolicy.authorize()` — binding, not advisory |
| Audit trail | 16 event types, database timestamps, acting service recorded |

---

## The recovery loop

```mermaid
flowchart TD
    A["💳 Payment at risk<br/>seeded or live webhook"] --> B["📋 Recovery case created"]
    B --> B2["🔬 Failure diagnosed<br/>why it failed"]
    B2 --> C["📊 Risk assessment<br/>risk + recoverability scored"]
    C --> D["🤖 Decision agent<br/>recommends a strategy"]
    D --> E{"🛡️ Policy check<br/>BINDING"}

    E -->|refused| F["🚫 Escalate to human<br/>0 attempts used"]
    E -->|authorised| G["⚡ Execute attempt"]

    G --> H{"🔍 Verify payment"}
    H -->|succeeded| I["✅ Record outcome<br/>Stop"]
    H -->|failed, attempts left| G
    H -->|failed, limit reached| J["⛔ Retry limit<br/>Escalate to human"]

    I --> K["📜 Audit trail"]
    F --> K
    J --> K

    style B2 fill:#D58A20,stroke:#B8761A,color:#fff
    style E fill:#635BFF,stroke:#4840D4,color:#fff
    style I fill:#15966F,stroke:#0F8A63,color:#fff
    style F fill:#D33F57,stroke:#B03047,color:#fff
    style J fill:#D33F57,stroke:#B03047,color:#fff
    style K fill:#0C2451,stroke:#0C2451,color:#fff
```

The diamond is the whole design. The agent *recommends*; the policy *decides*.
Execution is reachable only through an authorised policy decision.

---

## Failure diagnosis

Diagnosis runs **before** scoring, because a score cannot tell an expired card
apart from a bank timeout — and the right response to those two is not the same.

`PaymentDiagnosisService` reads the provider's failure reason and the case's
attempt history, then classifies into categories chosen for **what to do next**
rather than for how a provider spells its error codes.

| Category | `retry_viable` | Strategy it selects |
|---|---|---|
| `bank_timeout` | ✅ | `retry_payment` — transient, the charge may simply clear |
| `insufficient_funds` | ✅ | `send_reminder` — the customer needs time, not another attempt |
| `card_expired` | ❌ | `update_payment_method` — the instrument is dead |
| `payment_method_invalid` | ❌ | `update_payment_method` |
| `persistent_decline` | ❌ | `offer_alternative_method` |
| `gateway_uncertain` | ❌ | `escalate` — never guess at an ambiguous provider state |
| `unknown_failure` | ✅ | falls back to the recoverability bands |

Two rules make this more than a lookup table:

- **A repeated reason kills `retry_viable`.** The same failure twice is evidence
  it is not transient, whatever the category normally implies.
- **A cause that cannot clear on a retry is never retried.** If the diagnosis
  says `retry_viable` is false, `retry_payment` is rewritten to
  `offer_alternative_method` even where the recoverability score would have
  allowed the retry.

The diagnosis is carried into `authorize()` and recorded in the policy factors,
so the audit trail shows the cause that drove the decision — not just the score.

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
| **Not retry-viable** | from diagnosis | Retry is replaced, never repeated blindly |
| **Already recovered** | — | Stops; never retries a payment that has paid |
| **Concluded case** | — | Outcome cannot be recorded twice; no double-counting |
| **Duplicate case** | — | One open case per payment; re-ingestion returns the existing case |
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

Selection is diagnosis-first. Where the diagnosis carries no strategy signal, the
recoverability bands decide — so a case is never left without an action.

| Recoverability | Strategy | Reasoning |
|---|---|---|
| ≥ 80, first attempt | `retry_payment` | A transient failure; retrying is likely to clear it |
| ≥ 60 | `send_reminder` | The customer needs prompting, not another charge attempt |
| ≥ 40 | `update_payment_method` | The instrument itself is the obstacle |
| < 40, or risk ≥ 70 | `escalate` | Below the threshold where automation is appropriate |

All five actions — `retry_payment`, `send_reminder`, `update_payment_method`,
`offer_alternative_method`, `escalate` — are reachable, plus `manual_review` in
the domain and action layer.

---

## Architecture

```mermaid
flowchart TB
    WH["🔔 Razorpay webhook<br/>live payment.failed"]
    UI["⚛️ React 19 + Vite<br/>dashboard, agent controls, audit timeline"]
    API["🚀 FastAPI<br/>24 operations"]
    ORC["🧠 Recovery Orchestrator<br/>the closed loop"]

    subgraph domainlayer ["Decision layer"]
        DIAG["🔬 Payment diagnosis<br/>7 failure categories"]
        AG["Decision + Action agents"]
        POL["🛡️ Recovery policy<br/>AUTHORISATION BOUNDARY"]
    end

    subgraph servicelayer ["Services"]
        RISK["Risk assessment"]
        EXEC["Action execution"]
        OUT["Outcome recording"]
        AUD["Audit events"]
    end

    REPO["📚 Repositories"]
    DB[("🗄️ PostgreSQL<br/>Neon · 16 migrations")]
    SIM["🧪 Payment simulator<br/>test simulation"]

    WH -->|HTTP/JSON| API
    UI -->|HTTP/JSON| API
    API --> ORC
    ORC --> DIAG
    DIAG --> AG
    AG --> POL
    POL -->|authorised only| EXEC
    ORC --> RISK
    ORC --> OUT
    ORC --> AUD
    EXEC --> SIM
    RISK --> REPO
    EXEC --> REPO
    OUT --> REPO
    AUD --> REPO
    REPO --> DB

    style POL fill:#635BFF,stroke:#4840D4,color:#fff
    style DIAG fill:#D58A20,stroke:#B8761A,color:#fff
    style ORC fill:#0C2451,stroke:#0C2451,color:#fff
    style SIM fill:#D58A20,stroke:#B8761A,color:#fff
    style WH fill:#15966F,stroke:#0F8A63,color:#fff
```

Layered deliberately: API handlers stay thin, services hold the workflow,
repositories own persistence, and the domain has no framework imports at all.

```text
app/
├── agents/        decision and action agents
├── api/           FastAPI routers — thin, no business logic
├── core/          database engine and session
├── domain/        10 dataclasses + enums, zero framework dependencies
├── models/        SQLAlchemy ORM mappings
├── policies/      the authorisation boundary
├── repositories/  persistence, one per aggregate
├── services/      workflow, diagnosis, and the orchestrator
└── simulator/     seed data, reset, payment simulation
```

---

## Live webhook ingestion

`POST /webhooks/razorpay` accepts a genuine Razorpay `payment.failed` envelope,
tolerates a flat test payload, and is idempotent on `payment_id`:

```json
{
  "event": "payment.failed",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_QxT4mLk92",
        "amount": 499900,
        "error_description": "Card expired"
      }
    }
  }
}
```

It normalises paise to rupees, creates the customer and payment if they are new,
opens a recovery case through `RecoveryCaseService` — which returns the existing
open case rather than minting a duplicate — and records a `payment_failed` audit
event attributed to `razorpay_webhook`.

The dashboard's **Razorpay Integration Command Center** posts to the same
endpoint and refreshes the portfolio figures on success, so a live event can be
ingested and seen landing in the tiles during a demonstration.

```bash
curl -X POST http://127.0.0.1:8000/webhooks/razorpay \
  -H 'Content-Type: application/json' \
  -d '{"payment_id":"pay_live_demo","amount":7500,"failure_reason":"Card expired"}'
```

---

## The audit trail

Sixteen event types, written by the service that acted, timestamped by the
database. A completed recovery reads as a chronology:

```text
 1  failure_diagnosed     payment_diagnosis_service   bank_timeout (high): transient
 2  risk_assessed         risk_assessment_service     Risk 0, recoverability 100
 3  decision_generated    recovery_decision_agent     recommended retry_payment
 4  policy_checked        recovery_decision_policy    risk=0 retry=0/3 diagnosis=bank_timeout
 5  action_authorized     recovery_decision_policy    attempt 1/3 authorised
 6  action_executed       recovery_action_service     approved → started → done
 7  payment_verified      payment_simulator           TEST SIMULATION: succeeded
 8  outcome_recorded      recovery_outcome_service    4999.00 recovered
 9  recovery_completed    recovery_outcome_service    4999.00 of 4999.00
10  case_stopped          orchestrator                automation stopped
```

A refused case stops at the policy in four events. An exhausted case runs past a
dozen and ends in `retry_limit_reached` → `case_escalated`. Nothing is fabricated
in the frontend; every timestamp is the one stored in Postgres.

<details>
<summary><b>All 16 event types</b></summary>

<br />

| Event | Written by |
|---|---|
| `payment_received` / `payment_failed` | payment lifecycle, and the webhook |
| `failure_diagnosed` | `PaymentDiagnosisService` |
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

`GET /recovery-metrics` returns the portfolio without running anything, and
`POST /recovery-batch/run` processes open cases through the same orchestrator a
single case uses. Both call one shared `_portfolio_metrics()`, so the dashboard
and the batch cannot disagree — there is no separate "demo mode" that produces
nicer numbers.

Every figure is **re-read from the database after the run**, never accumulated by
the endpoint while looping:

```json
{
  "cases_processed": 3,
  "cases_remaining": 25,
  "total_revenue_at_risk": 438942.0,
  "recoverable_revenue": 120895.0,
  "revenue_recovered": 99045.0,
  "remaining_revenue_at_risk": 339897.0,
  "recovery_rate": 22.6,
  "recovered_cases": 18,
  "escalated_cases": 11,
  "mode": "test_simulation"
}
```

Three figures that are routinely conflated, kept separate here:

- **Revenue at risk** — every open case's amount.
- **Recoverable revenue** — only what the policy actually cleared for
  automation. A high-value or high-risk case is excluded, because the agent is
  not permitted to pursue it.
- **Actually recovered** — what came back, from recorded outcomes.

Two identities must always hold, and there are tests asserting both:

```text
revenue_recovered + remaining_revenue_at_risk == total_revenue_at_risk
recovered + failed + escalated + stopped + active == total cases
```

Recovered revenue is summed from the **latest outcome per case**, not from every
outcome row. Summing the rows counts a case twice whenever its outcome was
recorded more than once, and can report more money recovered than was ever at
risk — the quiet way most recovery dashboards inflate themselves. A partial
recovery contributes the amount that actually came back, not the full amount at
risk.

---

## API

<details open>
<summary><b>The agent</b></summary>

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/recovery-cases/{case_id}/run` | Run the full loop for one case |
| `POST` | `/recovery-batch/run?limit=N` | Run a bounded slice of open cases |
| `GET` | `/recovery-metrics` | Portfolio figures without running anything |
| `GET` | `/recovery-policy` | The guardrails actually enforced |

</details>

<details open>
<summary><b>Live ingestion</b></summary>

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/webhooks/razorpay` | Ingest a live `payment.failed` event |

</details>

<details>
<summary><b>Cases, assessment, decisions</b></summary>

| Method | Route |
|---|---|
| `GET` | `/recovery-cases` |
| `POST` | `/recovery-cases/{payment_id}` |
| `GET` | `/recovery-cases/{case_id}` |
| `POST` | `/recovery-cases/{case_id}/risk-assessments` |
| `POST` | `/recovery-cases/{case_id}/decisions` · `/decisions/ai` · `/ai-decision` |

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
> is what the interface uses. The terminal-state guard on outcome recording does
> apply here, so a concluded case cannot be recorded twice by either path.

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
python -m app.simulator.seed          # 22 payments across every scenario
python -m app.simulator.reset_cases   # clean, repeatable starting state
uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

> The API allowlists `localhost` and `127.0.0.1` on the usual Vite ports. They
> are different origins to a browser, so open the host the dev server prints —
> mixing them is the fastest way to see a spurious "SYSTEM OFFLINE".

---

## Try the agent

The seeded batch is engineered so each scenario is reachable and reproducible.

| Try this | Payment | What happens |
|---|---|---|
| 🟢 **Clean recovery** | `pay_2004` | `bank_timeout` diagnosed · recovers on attempt 1 |
| 🟡 **Retry ladder** | `pay_2001` | Fails, retries, recovers on a later attempt |
| 🔴 **Exhausted** | `pay_2014` | 3 of 3 attempts fail · `maximum_retry_limit_reached` · escalated |
| 🛑 **Refused** | `pay_2011` | **0 attempts** · `high_risk_case` · policy blocked it |
| 💰 **High value** | `pay_2020` | ₹75,000 · `high_value_requires_policy_review` |
| 🔬 **Diagnosis overrides score** | `pay_2005` | Not retry-viable · retry replaced, not repeated |

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
python -m pytest -q                    # 113 tests
python -m pytest tests/unit -q         # 79, no database, ~3s
python -m pytest tests/integration -q  # 34, hits the database
python -m app.simulator.reset_cases    # reset afterwards
```

```text
111 passed, 2 failed
```

The suite covers the diagnosis classifier and its category mapping, the strategy
table, every guardrail in `authorize()`, the simulator's determinism, the retry
ladder at each attempt, stop-on-success, duplicate-execution blocking, audit
event ordering, and the batch metric identities.

One test exists purely to fail loudly if the strategy table ever regresses to
returning `retry_payment` for everything — the failure mode this system is
designed to avoid.

**Two integration tests are currently red, and both are stale expectations
rather than product defects.** They are named in [Known limits](#known-limits).

> Integration tests write to the configured database. Run
> `python -m app.simulator.reset_cases` afterwards before demonstrating.

---

## Known limits

Stated plainly, because a submission that hides its edges is worse than one that
names them.

| Limit | Detail |
|---|---|
| **Two failing tests** | `test_a_case_with_repeated_outcomes_is_counted_once` builds duplicate outcomes to prove the metrics de-duplicate them — the new terminal-state guard now refuses to create the duplicates, so its premise no longer holds. `test_get_audit_events_for_case` asserts two events on a new case; diagnosis adds a third. Both assertions predate the behaviour they now contradict. |
| **Batch latency** | A full retry ladder costs ~40 commits. Against a remote database that is seconds per case; the endpoint is chunked via `?limit=N` so no single request times out. The real fix is one transaction per case. |
| **Manual endpoints are ungated** | The lifecycle routes bypass `authorize()` by design, as operator tools. Only the orchestrated path is bounded. |
| **No partial recovery from automation** | The orchestrator records `recovered` or `not_recovered`. Partial outcomes are reachable through the manual outcome flow. |
| **`FAILED` is unreachable by the agent** | An orchestrated case ends `recovered`, `escalated`, or `stopped`. `FAILED` arrives only from a manual "not recovered", so a batch run will never produce it. |
| **Webhook is unauthenticated** | `POST /webhooks/razorpay` does not verify the Razorpay signature header. Fine for a prototype; not something to expose. |
| **Simulated execution** | No payment provider integration. See the notice at the top. |
| **No authentication** | Every endpoint is open. This is a prototype, not a deployed product. |

---

## Roadmap

- Realign the two stale test assertions with the guards that superseded them
- Razorpay signature verification on the webhook endpoint
- One transaction per case, cutting batch latency by an order of magnitude
- Policy authorisation on the manual endpoints, closing the operator gap
- Live payment-provider execution behind the existing simulator interface
- Partial recovery as a first-class orchestrated outcome
- Recovery-window enforcement against case age
- Historical performance: which strategy actually recovers most, by segment

---

<div align="center">

### Built for the Razorpay Buildathon — Track 3

**Lakkarsu Nanditha**

*Don't just detect failed payments. Work out why they failed, decide what to do,
act within limits you cannot exceed, measure what came back, and keep the
receipts.*

<br />

[![Dashboard](https://img.shields.io/badge/Live_Dashboard-635BFF?style=for-the-badge&logo=vercel&logoColor=white)](https://recover-ai-virid.vercel.app)
[![API Docs](https://img.shields.io/badge/API_Docs-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://recoverai-3at6.onrender.com/docs)

</div>
