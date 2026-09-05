# RecoverAI — AI-Assisted Revenue Recovery Platform

> An AI-assisted revenue recovery platform that identifies revenue at risk, assesses recovery cases, recommends bounded recovery actions, executes controlled recovery workflows, tracks outcomes, and maintains an auditable history of recovery activity.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-Frontend-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-2C5D63)](https://alembic.sqlalchemy.org/)
[![Testing](https://img.shields.io/badge/Testing-Pytest-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)

---

## Overview

RecoverAI is an AI-assisted revenue recovery platform built for the **AI Revenue Recovery** problem space of the Razorpay Buildathon.

The platform focuses on a practical problem faced by businesses: a failed or degraded payment does not necessarily mean that the revenue is permanently lost. A payment may fail because of a temporary issue, customer-related circumstances, payment-method problems, or other conditions. Simply detecting the failure is therefore not enough.

RecoverAI turns a payment problem into a structured recovery workflow:

**Detection → Recovery Case → Risk Assessment → AI Decision → Recovery Action → Execution → Outcome → Audit**

The system combines backend services, domain models, AI-assisted agents, recovery policies, persistence, API endpoints, and a React frontend to provide an end-to-end recovery workflow.

---

## The Recovery Agent

RecoverAI is an AI-assisted revenue recovery **agent**: it takes a
payment that failed, decides what to do about it, does it within
explicit limits, checks whether it worked, and stops.

### The loop

```text
DETECT        a payment at risk becomes a recovery case
   ↓
ASSESS        risk and recoverability are scored from the payment
   ↓          and its attempt history
DECIDE        the agent recommends one of five recovery strategies
   ↓
POLICY CHECK  the policy authorises, refuses, or escalates
   ↓          — this is binding, not advisory
EXECUTE       the authorised action runs, up to 3 attempts
   ↓
VERIFY        the payment result is checked after each attempt
   ↓
RECOVER       stop on success, or escalate to a human on exhaustion
or ESCALATE
   ↓
AUDIT         every step above is written to an immutable trail
```

Run it for one case with `POST /recovery-cases/{case_id}/run`, or across
the open portfolio with `POST /recovery-batch/run`.

### Bounded automation

The agent recommends; the policy decides. A recommendation cannot reach
execution unless `RecoveryDecisionPolicy.authorize()` returns it as
authorised, so the decision layer has no path around the guardrails.

| Guardrail | Limit | Behaviour |
|---|---|---|
| Max retries | 3 | Stops and escalates on exhaustion |
| Recovery window | 7 days | Configurable bound on the recovery period |
| High risk | score ≥ 70 | Escalates to a human, executes nothing |
| High value | ≥ ₹50,000 | Requires policy review before automation |
| Already recovered | — | Stops; never retries a paid payment |
| Closed case | — | Skipped; duplicate execution is blocked |

The live values are served by `GET /recovery-policy` and rendered
directly in the interface, so the displayed limits cannot drift from the
enforced ones.

### Recovery strategies

The decision layer selects between `retry_payment`, `send_reminder`,
`update_payment_method`, `offer_alternative_method` and `escalate` based
on the assessed recoverability — a high-recoverability case is retried,
a moderate one is prompted, a weak one has its payment method
questioned, and a high-risk one goes to a human.

### Human escalation

Two distinct paths end with a human, and the audit trail distinguishes
them:

- **`high_risk_case`** — refused before execution, `0` attempts used
- **`maximum_retry_limit_reached`** — executed and exhausted, `3` attempts used

### Measured recovery

`POST /recovery-batch/run` processes open cases and returns totals that
are **re-read from the database after the run**, never accumulated by
the endpoint. Recovered revenue is summed from recovery outcomes, so a
partial recovery contributes the amount that actually came back rather
than the full amount at risk.

### Audit trail

Every stage writes an event: `risk_assessed`, `decision_generated`,
`policy_checked`, `action_authorized`, `action_executed`,
`payment_verified`, `retry_attempted`, `retry_limit_reached`,
`outcome_recorded`, `recovery_completed`, `case_stopped`,
`case_escalated`. Each carries a database timestamp, the acting service,
and the case it belongs to.

### Test simulation — important

**Recovery execution is simulated. No payment provider is contacted and
no real money moves.** `app/simulator/payment_simulator.py` derives each
attempt's result deterministically from the payment id, the attempt
number and the assessed recoverability, so a demonstration replays
identically. Every simulated result is labelled `test_simulation` in the
API response, the audit reason, and the interface.

The recovery *engine* — assessment, decision, policy, execution
lifecycle, outcome recording and audit — is real application code
operating on real database records. Only the payment provider is
simulated.

There is **no LLM in this system.** The decision layer is deterministic
policy code, which is what makes its behaviour testable and its refusals
explainable.

### Trying it

```bash
python -m app.simulator.seed
python -m app.simulator.reset_cases
```

| Scenario | Payment | Expected |
|---|---|---|
| Recovers first attempt | `pay_2004` | `payment_recovered`, 1 attempt |
| Exhausts retries | `pay_2014` | `maximum_retry_limit_reached`, 3 attempts, escalated |
| Refused by policy | `pay_2011` | `high_risk_case`, **0 attempts**, escalated |
| High value review | `pay_2020` | `high_value_requires_policy_review`, 0 attempts |

```bash
python -m pytest -q
```
## Problem Statement

Revenue leakage can occur when payments fail or remain unresolved.

A conventional payment system may tell a business that a transaction failed, but a revenue recovery workflow needs to go further:

- What is the recovery case?
- How significant is the revenue at risk?
- What is the risk associated with the case?
- What recovery strategy should be considered?
- Which action is appropriate?
- Should that action be executed?
- What happened after the action?
- Was revenue recovered?
- Can the complete process be audited?

RecoverAI is designed to connect these stages into a single workflow rather than treating payment failure, decision-making, action execution, and recovery measurement as isolated operations.

---

## Razorpay Buildathon Track

RecoverAI is aligned with the **AI Revenue Recovery** track of the Razorpay Buildathon.

The track asks teams to build an agent capable of detecting revenue at risk, determining an appropriate intervention, and executing a bounded recovery workflow.

RecoverAI implements this concept through a controlled architecture:

```text
Revenue at Risk
       │
       ▼
Recovery Case
       │
       ▼
Risk Assessment
       │
       ▼
AI-Assisted Decision
       │
       ▼
Recovery Action
       │
       ▼
Controlled Execution
       │
       ▼
Recovery Outcome
       │
       ▼
Audit Trail
```

The important design principle is that AI-assisted decision making is combined with **bounded actions, explicit policies, outcome tracking, and auditability** rather than allowing unrestricted automation.

---

## Objectives

RecoverAI is designed to:

1. Identify and structure revenue-recovery opportunities.
2. Represent payment problems as recovery cases.
3. Assess the risk associated with recovery cases.
4. Use AI-assisted decision logic to recommend recovery strategies.
5. Apply recovery decision policies before actions are executed.
6. Generate bounded recovery actions.
7. Execute actions through a dedicated service layer.
8. Record recovery outcomes.
9. Track recovered revenue.
10. Maintain an audit trail of important recovery events.
11. Expose the recovery workflow through backend APIs.
12. Provide a frontend interface for monitoring and operating recovery cases.
13. Maintain separation between domain logic, services, persistence, APIs, and presentation.

---

# System Architecture

RecoverAI follows a layered architecture where each major responsibility is separated into its own component.

```text
                         ┌──────────────────────┐
                         │    React Frontend    │
                         │   Dashboard / UI     │
                         └──────────┬───────────┘
                                    │
                                    │ HTTP / JSON
                                    ▼
                         ┌──────────────────────┐
                         │     FastAPI API      │
                         │     API Layer        │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │ Recovery Case  │ │ Risk Assessment│ │ Recovery       │
        │ APIs / Service │ │ APIs / Service │ │ Decision APIs  │
        └────────┬───────┘ └────────┬───────┘ └────────┬───────┘
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │     AI Agents        │
                         │                      │
                         │ Decision Agent       │
                         │ Action Agent         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Recovery Policies    │
                         │ Bounded Decisions    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Recovery Action      │
                         │ Execution Service    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Recovery Outcomes    │
                         │ & Recovered Revenue  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     Audit Events     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ SQL Database / ORM   │
                         │ SQLAlchemy + Alembic │
                         └──────────────────────┘
```

---

# End-to-End Recovery Workflow

A recovery case moves through several stages.

## 1. Payment / Revenue Risk

A payment and its associated attempts provide the starting point for identifying a recovery opportunity.

The system maintains structured information about:

- Customers
- Payments
- Payment attempts
- Recovery cases

---

## 2. Recovery Case Creation

A failed or problematic payment can be represented as a **Recovery Case**.

The recovery case becomes the central object connecting the different stages of the recovery workflow.

It provides a structured representation of the revenue that requires recovery attention.

---

## 3. Risk Assessment

The system performs a risk assessment for the recovery case.

The risk-assessment layer provides structured information that can be used by downstream recovery decision logic.

This allows the recovery workflow to consider the characteristics of a case instead of applying exactly the same recovery approach to every payment failure.

---

## 4. AI-Assisted Recovery Decision

RecoverAI contains a dedicated **Recovery Decision Agent**.

The agent is responsible for AI-assisted recovery decision logic.

The decision is not treated as an unrestricted command. It is passed through the application's recovery decision policy and service layers.

Conceptually:

```text
Recovery Case
     │
     ▼
Risk Assessment
     │
     ▼
Recovery Decision Agent
     │
     ▼
Recovery Decision
     │
     ▼
Decision Policy
     │
     ▼
Approved / Bounded Recovery Action
```

This separation makes the AI decision process easier to inspect, test, and control.

---

## 5. Recovery Action Generation

Once a recovery strategy has been determined, RecoverAI creates a structured recovery action.

Recovery actions are represented as first-class domain and persistence objects rather than being hidden inside a single API operation.

This provides a clear distinction between:

- What the system decided
- What action was created
- Whether the action was executed
- What happened after execution

---

## 6. Controlled Action Execution

Recovery action execution is handled through a dedicated execution service.

This provides a controlled boundary between deciding an action and actually executing it.

```text
AI Decision
     │
     ▼
Policy Validation
     │
     ▼
Recovery Action
     │
     ▼
Execution Service
     │
     ▼
Execution Result
```

The execution layer also integrates with audit-event recording so that important recovery operations remain traceable.

---

## 7. Recovery Outcome

After an action has been executed, its result can be recorded as a **Recovery Outcome**.

The outcome records whether the recovery attempt was successful and can capture the amount of revenue recovered.

This creates the measurement stage of the workflow:

```text
Recovery Action
      │
      ▼
Execution
      │
      ▼
Outcome
      │
      ▼
Amount Recovered
```

---

## 8. Audit Trail

RecoverAI includes an audit-event layer for tracking important operations throughout the recovery lifecycle.

The audit trail is designed to provide visibility into:

- Recovery decisions
- Recovery actions
- Action execution
- Recovery outcomes
- Important recovery-case events

This makes the recovery process easier to inspect and understand after an operation has taken place.

---

# Core Components

## AI Agents

The project contains dedicated agents for recovery decision making and recovery action generation.

### Recovery Decision Agent

Located at:

```text
app/agents/recovery_decision_agent.py
```

Responsible for AI-assisted recovery decision logic.

### Recovery Action Agent

Located at:

```text
app/agents/recovery_action_agent.py
```

Responsible for generating structured recovery actions based on the recovery workflow.

---

# Backend Architecture

The backend is implemented using **Python and FastAPI**.

The backend is separated into several layers.

```text
app/
├── agents/
├── api/
├── core/
├── domain/
├── models/
├── policies/
├── repositories/
├── services/
└── simulator/
```

Each layer has a specific responsibility.

---

## API Layer

Located in:

```text
app/api/
```

The API layer exposes the recovery workflow through FastAPI endpoints.

The project includes APIs for:

- Recovery cases
- Risk assessments
- Recovery decisions
- Recovery actions
- Recovery outcomes
- Audit events

The API layer communicates with the service layer instead of placing the complete business workflow directly inside route handlers.

---

## Service Layer

Located in:

```text
app/services/
```

The service layer contains application-level business workflows.

Implemented service areas include:

- Recovery case service
- Risk assessment service
- Recovery decision service
- Recovery action service
- Recovery action execution service
- Recovery outcome service
- Audit event service

This separation keeps API handlers lightweight and places business operations inside reusable service components.

---

## Domain Layer

Located in:

```text
app/domain/
```

The domain layer represents core business concepts within RecoverAI.

The project contains domain representations for:

- Customer
- Payment
- Payment attempt
- Recovery case
- Recovery decision
- Recovery action
- Recovery outcome
- Risk assessment
- Audit event

This allows the recovery workflow to be represented using explicit business concepts rather than loosely structured data.

---

## Repository Layer

Located in:

```text
app/repositories/
```

Repositories provide persistence-related operations for the application's entities.

The project includes repositories for:

- Customers
- Payments
- Payment attempts
- Recovery cases
- Recovery decisions
- Recovery actions
- Recovery outcomes
- Risk assessments
- Audit events

This separates database access from higher-level business logic.

---

## Policy Layer

Located in:

```text
app/policies/
```

The recovery decision policy provides an additional control layer around recovery decisions.

This is important for the project's **bounded recovery** approach.

Instead of allowing an AI component to directly perform arbitrary operations, the application separates:

```text
AI Recommendation
        ↓
Policy
        ↓
Allowed Recovery Decision
```

---

# Data Model

RecoverAI uses SQLAlchemy for ORM-based database interaction and Alembic for schema migrations.

The main entities are:

```text
Customer
   │
   └── Payment
          │
          └── Payment Attempt
                 │
                 └── Recovery Case
                        ├── Risk Assessment
                        ├── Recovery Decision
                        ├── Recovery Action
                        │       │
                        │       └── Execution
                        │
                        ├── Recovery Outcome
                        │
                        └── Audit Events
```

The database structure is maintained through versioned Alembic migrations.

---

# Database & Migrations

Database configuration is handled through:

```text
app/core/database.py
```

Database schema evolution is managed using **Alembic**.

Migration files are stored under:

```text
alembic/versions/
```

The migration history covers the creation and relationships of the major recovery entities, including:

- Customers
- Payments
- Payment attempts
- Recovery cases
- Risk assessments
- Recovery decisions
- Recovery actions
- Recovery outcomes
- Audit events

Foreign-key migrations are also used to connect related recovery entities.

This allows the database schema to evolve in a controlled and reproducible manner.

---

# Frontend

The frontend is implemented using:

- React
- Vite
- JavaScript
- CSS
- Lucide React icons

The frontend source code is located under:

```text
frontend/src/
```

Main frontend files include:

```text
frontend/
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
└── src/
    ├── api.js
    ├── App.jsx
    ├── App.css
    ├── index.css
    └── main.jsx
```

---

## Frontend Responsibilities

The React frontend provides an interface for interacting with the recovery platform.

It communicates with the backend through the API layer.

The frontend API module:

```text
frontend/src/api.js
```

contains functions for communicating with recovery-related backend endpoints, including operations related to:

- Recovery cases
- Recovery decisions
- Recovery actions
- Recovery outcomes
- Audit events

The separation of API communication from the main React application keeps frontend data-access logic organized.

---

# API Flow

The overall application communication can be represented as:

```text
React UI
   │
   ▼
frontend/src/api.js
   │
   │ HTTP / JSON
   ▼
FastAPI
   │
   ▼
API Routes
   │
   ▼
Services
   │
   ├── Agents
   ├── Policies
   └── Repositories
           │
           ▼
       Database
```

This architecture allows the frontend to remain independent of the backend's internal implementation details.

---

# API Areas

The backend currently organizes recovery functionality around the following API modules:

```text
app/api/
├── recovery_cases.py
├── risk_assessments.py
├── recovery_decisions.py
├── recovery_actions.py
├── recovery_outcomes.py
└── audit_events.py
```

These APIs collectively expose the main stages of the recovery lifecycle.

The application entry point is:

```text
app/main.py
```

---

# Testing

RecoverAI includes both **unit tests and integration tests**.

The testing structure is:

```text
tests/
├── unit/
├── integration/
└── evaluation/
```

The tests cover important areas including:

### Unit Testing

Unit tests cover components such as:

- Payment domain logic
- Recovery decision agent
- Recovery action agent
- Recovery decision policy
- Recovery decision service
- Recovery action service
- Recovery action execution
- Recovery outcome service
- Risk assessment service
- Recovery action domain behavior

### Integration Testing

Integration tests cover workflows and APIs such as:

- Recovery flow
- AI decision API
- AI recovery action API
- Recovery action execution API
- Recovery outcome API
- Risk assessment API
- Audit event API

The test suite is intended to validate both individual components and the interaction between major parts of the recovery workflow.

---

# Project Structure

```text
recoverai/
│
├── app/
│   ├── agents/
│   │   ├── recovery_action_agent.py
│   │   └── recovery_decision_agent.py
│   │
│   ├── api/
│   │   ├── audit_events.py
│   │   ├── recovery_actions.py
│   │   ├── recovery_cases.py
│   │   ├── recovery_decisions.py
│   │   ├── recovery_outcomes.py
│   │   └── risk_assessments.py
│   │
│   ├── core/
│   │   └── database.py
│   │
│   ├── domain/
│   │   ├── audit_event.py
│   │   ├── customer.py
│   │   ├── payment.py
│   │   ├── payment_attempt.py
│   │   ├── recovery_action.py
│   │   ├── recovery_case.py
│   │   ├── recovery_decision.py
│   │   ├── recovery_outcome.py
│   │   └── risk_assessment.py
│   │
│   ├── models/
│   │   ├── audit_event.py
│   │   ├── base.py
│   │   ├── customer.py
│   │   ├── payment.py
│   │   ├── payment_attempt.py
│   │   ├── recovery_action.py
│   │   ├── recovery_case.py
│   │   ├── recovery_decision.py
│   │   ├── recovery_outcome.py
│   │   └── risk_assessment.py
│   │
│   ├── policies/
│   │   └── recovery_decision_policy.py
│   │
│   ├── repositories/
│   │   ├── audit_event_repository.py
│   │   ├── customer_repository.py
│   │   ├── payment_attempt_repository.py
│   │   ├── payment_repository.py
│   │   ├── recovery_action_repository.py
│   │   ├── recovery_case_repository.py
│   │   ├── recovery_decision_repository.py
│   │   ├── recovery_outcome_repository.py
│   │   └── risk_assessment_repository.py
│   │
│   ├── services/
│   │   ├── audit_event_service.py
│   │   ├── recovery_action_execution_service.py
│   │   ├── recovery_action_service.py
│   │   ├── recovery_case_service.py
│   │   ├── recovery_decision_service.py
│   │   ├── recovery_outcome_service.py
│   │   └── risk_assessment_service.py
│   │
│   ├── simulator/
│   │
│   └── main.py
│
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
├── tests/
│   ├── evaluation/
│   ├── integration/
│   └── unit/
│
├── alembic.ini
├── requirements.txt
├── .gitignore
└── README.md
```

---

# Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Frontend Build Tool | Vite |
| Frontend Icons | Lucide React |
| Backend | Python |
| API Framework | FastAPI |
| ORM | SQLAlchemy |
| Database Migration | Alembic |
| Testing | Pytest |
| API Communication | HTTP / JSON |
| Architecture | Layered / Service-oriented backend |

---

# Installation

## 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd recoverai
```

## 2. Create a Python Virtual Environment

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

## 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

## 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

# Environment Configuration

RecoverAI uses environment configuration for local development.

Create a local `.env` file based on the configuration required by the application.

**Do not commit secrets, API keys, credentials, or private environment configuration to GitHub.**

The repository's `.gitignore` is configured to keep environment and generated files out of source control.

---

# Running the Backend

From the project root, activate the virtual environment and start the FastAPI application.

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

The API will be available locally through the configured FastAPI development server.

FastAPI also provides interactive API documentation through its standard documentation endpoints.

---

# Running the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite will start the React development server and provide the local frontend URL.

---

# Database Migrations

To apply the existing Alembic migrations:

```bash
alembic upgrade head
```

To create a new migration during development:

```bash
alembic revision --autogenerate -m "describe migration"
```

Then apply it using:

```bash
alembic upgrade head
```

---

# Example Recovery Scenario

A simplified recovery scenario looks like this:

```text
1. A payment fails
        │
        ▼
2. A recovery case is created
        │
        ▼
3. The case is assessed for risk
        │
        ▼
4. AI-assisted logic evaluates the case
        │
        ▼
5. A recovery decision is generated
        │
        ▼
6. The decision policy validates the recovery path
        │
        ▼
7. A bounded recovery action is created
        │
        ▼
8. The action execution service executes the action
        │
        ▼
9. The recovery result is recorded
        │
        ▼
10. Recovered amount is tracked
        │
        ▼
11. Relevant events are recorded in the audit trail
```

This creates a complete feedback loop from identifying revenue risk to measuring the recovery result.

---

# Design Principles

## 1. Bounded AI

AI-assisted decisions are separated from action execution.

The system uses explicit application logic and recovery policies to control how recovery decisions progress into actions.

---

## 2. Separation of Concerns

The backend separates:

```text
API
 ↓
Service
 ↓
Domain / Policy / Agent
 ↓
Repository
 ↓
Database
```

This makes the application easier to test, maintain, and extend.

---

## 3. Auditability

Important recovery events are represented through audit-event functionality.

This provides visibility into what happened during the recovery lifecycle.

---

## 4. Outcome-Based Recovery

The system does not stop after recommending or executing an action.

Recovery outcomes are recorded so that the workflow can distinguish between:

```text
Decision
   ≠
Action
   ≠
Execution
   ≠
Recovered Revenue
```

This is important when evaluating whether a recovery strategy actually produced a useful result.

---

## 5. Extensibility

The layered design allows additional recovery strategies, policies, agents, APIs, and frontend capabilities to be added without requiring the entire application to be rewritten.

---

# Why RecoverAI Is Different

Many payment systems focus primarily on processing transactions and reporting failures.

RecoverAI focuses on the **post-failure recovery lifecycle**.

Instead of:

```text
Payment Failed
      ↓
End
```

RecoverAI follows:

```text
Payment Failed
      ↓
Identify Revenue Risk
      ↓
Create Recovery Case
      ↓
Assess Risk
      ↓
Determine Recovery Strategy
      ↓
Generate Bounded Action
      ↓
Execute
      ↓
Measure Result
      ↓
Record Audit Trail
```

The goal is to move from **payment failure detection** toward **structured revenue recovery**.

---

# Current Scope

The current implementation includes:

- Recovery case management
- Risk assessment
- AI-assisted recovery decision logic
- AI-assisted recovery action logic
- Recovery decision policies
- Recovery action execution service
- Recovery outcome tracking
- Recovered amount tracking
- Audit-event functionality
- Repository-based persistence
- SQLAlchemy models
- Alembic migrations
- FastAPI APIs
- React frontend
- Unit tests
- Integration tests

---

# Future Enhancements

Potential future improvements include:

- Integration with live payment providers
- More payment-failure reason classification
- Additional recovery strategies
- More advanced customer segmentation
- Historical recovery-performance analysis
- Recovery strategy optimization based on outcomes
- Automated retry scheduling
- Notification integrations
- Analytics and recovery dashboards
- More sophisticated AI evaluation
- Human approval workflows for sensitive actions
- Production-grade authentication and authorization
- Observability, metrics, and monitoring
- Deployment using containerized infrastructure

---

# Limitations

RecoverAI is currently a project implementation and prototype rather than a production payment-recovery system.

In a production environment, additional concerns would need to be addressed, including:

- Production payment-provider integrations
- Authentication and authorization
- Secure secret management
- Rate limiting
- Production database infrastructure
- Distributed execution
- Idempotency guarantees
- Monitoring and observability
- Compliance requirements
- Production-grade notification providers
- Advanced model evaluation and governance

These are intentionally separated from the core project implementation so that the current system can demonstrate the complete recovery architecture and workflow.

---

# Project Outcome

RecoverAI demonstrates how an AI-assisted system can connect revenue-risk detection, decision making, controlled recovery actions, outcome measurement, and auditability into one structured workflow.

The central idea is:

> **Don't just identify failed payments. Build a controlled system that decides what to do next, executes the recovery workflow, measures the result, and keeps the process traceable.**

---

# Buildathon Context

**Track:** AI Revenue Recovery  
**Platform:** Razorpay Buildathon  
**Project:** RecoverAI

RecoverAI was developed as a project exploring how agentic AI and structured backend architecture can be applied to revenue recovery.

The implementation emphasizes:

- AI-assisted decision making
- Bounded recovery actions
- End-to-end workflow orchestration
- Measurable recovery outcomes
- Auditability
- Modular backend architecture
- A usable frontend interface

---

# Author

**Lakkarsu Nanditha**

---

## License

This project was developed as part of a hackathon/buildathon project and is intended for educational, demonstration, and prototype purposes.
