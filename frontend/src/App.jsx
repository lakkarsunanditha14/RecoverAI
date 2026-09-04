import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  CreditCard,
  LayoutDashboard,
  Menu,
  RefreshCw,
  ShieldCheck,
  Target,
  X,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  approveRecoveryAction,
  recordRecoveryOutcome,
  startRecoveryAction,
  completeRecoveryAction,
  checkHealth,
  createAIDecision,
  createAIRecoveryAction,
  createRecoveryCase,
  createRiskAssessment,
  getRecoveryCase,
  getRecoveryCases,
  getAuditEvents,
  getRecentAuditEvents,
  getRecoveryOutcomes,
} from "./api";
import "./App.css";

const rupees = (value) =>
  `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

// Derived from the cases the dashboard already loaded. There is no
// historical snapshot to compare against, so each tile describes the
// current figure rather than a change over time.
const CLOSED_STATUSES = new Set([
  "recovered",
  "partially_recovered",
  "failed",
  "stopped",
]);

// Case statuses grouped into the four outcomes the pipeline bar shows.
// Kept to four so each segment can carry a readable label.
const PIPELINE_BUCKETS = [
  {
    key: "open",
    label: "Open",
    color: "var(--warning)",
    match: (status) => !CLOSED_STATUSES.has(status),
  },
  {
    key: "recovered",
    label: "Recovered",
    color: "var(--success)",
    match: (status) => status === "recovered",
  },
  {
    key: "partial",
    label: "Partially recovered",
    color: "var(--primary)",
    match: (status) => status === "partially_recovered",
  },
  {
    key: "unrecovered",
    label: "Not recovered",
    color: "var(--danger)",
    match: (status) => status === "failed" || status === "stopped",
  },
];

function buildSummary(cases) {
  const sum = (list, pick) =>
    list.reduce((running, item) => running + Number(pick(item)), 0);

  const atRisk = sum(cases, (item) => item.amount_at_risk);

  // Taken from the outcomes rather than the case amount: a partial
  // recovery brings back less than the case was worth, and counting the
  // whole amount (or nothing at all) misstates it in both directions.
  const recovered = sum(cases, (item) => item.amount_recovered ?? 0);

  const open = cases.filter((item) => !CLOSED_STATUSES.has(item.status));

  // Averaged over assessed cases only. An unassessed case has no
  // recoverability, and counting it as zero would drag the mean down as
  // though it had been assessed and found unrecoverable.
  const assessed = cases.filter(
    (item) =>
      item.recoverability_score !== null &&
      item.recoverability_score !== undefined
  );

  return {
    total: cases.length,
    assessedCount: assessed.length,
    recoverability: assessed.length
      ? Math.round(
          sum(assessed, (item) => item.recoverability_score) / assessed.length
        )
      : null,
    atRisk,
    recovered,
    outstanding: Math.max(atRisk - recovered, 0),
    openCount: open.length,
    closedCount: cases.length - open.length,
    // By value, not by case count: recovering 24,999 of 55,445 is a very
    // different result from recovering 899 of it, and counting cases
    // treats them the same.
    rate: atRisk ? Math.round((recovered / atRisk) * 100) : 0,
    pipeline: PIPELINE_BUCKETS.map((bucket) => ({
      ...bucket,
      count: cases.filter((item) => bucket.match(item.status)).length,
    })).filter((bucket) => bucket.count > 0),
  };
}

function buildStats(summary) {
  const { atRisk, recovered, outstanding, openCount, closedCount, rate } =
    summary;

  return [
    {
      label: "Revenue at Risk",
      value: rupees(outstanding),
      detail: `${openCount} open ${openCount === 1 ? "case" : "cases"}`,
      icon: AlertTriangle,
      tone: "danger",
    },
    {
      label: "Revenue Recovered",
      value: rupees(recovered),
      detail: `of ${rupees(atRisk)} at risk`,
      icon: Target,
      tone: "success",
    },
    {
      label: "Recovery Rate",
      value: `${rate}%`,
      detail: "by value recovered",
      icon: RefreshCw,
      tone: "primary",
    },
    {
      label: "Recovery Cases",
      value: String(summary.total),
      detail: `${closedCount} closed`,
      icon: CreditCard,
      tone: "warning",
    },
  ];
}

const CASE_STATUS_LABELS = {
  created: { text: "Action Required", tone: "warning" },
  investigating: { text: "Investigating", tone: "neutral" },
  decision_ready: { text: "Decision Ready", tone: "primary" },
  executing: { text: "Executing", tone: "primary" },
  verifying: { text: "Verifying", tone: "primary" },
  recovered: { text: "Recovered", tone: "success" },
  partially_recovered: { text: "Partially Recovered", tone: "success" },
  failed: { text: "Failed", tone: "danger" },
  stopped: { text: "Stopped", tone: "neutral" },
  escalated: { text: "Escalated", tone: "danger" },
};

// The risk band comes from the assessed score. It used to be derived from
// the case status, which reported a recovered case as "Low" risk and had
// nothing to do with the assessment.
function riskBand(score) {
  if (score === null || score === undefined) {
    return { text: "Not assessed", tone: "neutral" };
  }

  if (score >= 70) return { text: `High · ${score.toFixed(0)}`, tone: "danger" };
  if (score >= 40)
    return { text: `Medium · ${score.toFixed(0)}`, tone: "warning" };

  return { text: `Low · ${score.toFixed(0)}`, tone: "success" };
}

const EVENT_LABELS = {
  payment_received: { title: "Payment received", icon: CheckCircle2 },
  payment_failed: { title: "Payment failed", icon: AlertTriangle },
  risk_assessed: { title: "Risk assessment completed", icon: ShieldCheck },
  action_proposed: { title: "Recovery action proposed", icon: Zap },
  policy_checked: { title: "Policy checked", icon: ShieldCheck },
  action_executed: { title: "Recovery action executed", icon: Zap },
  outcome_recorded: { title: "Outcome recorded", icon: Target },
  recovery_completed: { title: "Recovery completed", icon: CheckCircle2 },
  case_escalated: { title: "Case escalated", icon: AlertTriangle },
  case_stopped: { title: "Case stopped", icon: X },
};

function relativeTime(isoString) {
  // The backend stores naive UTC timestamps, so mark them as UTC before
  // comparing: parsing them as local time puts every event in the future.
  const then = new Date(
    isoString.endsWith("Z") ? isoString : `${isoString}Z`
  );
  const seconds = Math.round((Date.now() - then.getTime()) / 1000);

  if (seconds < 60) return "just now";

  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} ${hours === 1 ? "hour" : "hours"} ago`;

  const days = Math.round(hours / 24);
  return `${days} ${days === 1 ? "day" : "days"} ago`;
}

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");

  const [recoveryCases, setRecoveryCases] = useState([]);
  const summary = useMemo(() => buildSummary(recoveryCases), [recoveryCases]);
  const stats = useMemo(() => buildStats(summary), [summary]);
  const [recoveryCase, setRecoveryCase] = useState(null);
  const [caseLoading, setCaseLoading] = useState(true);
  const [caseError, setCaseError] = useState("");

  const [riskAssessment, setRiskAssessment] = useState(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState("");

  const [aiDecision, setAiDecision] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");

  const [recoveryAction, setRecoveryAction] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState("");

  const [recoveryOutcome, setRecoveryOutcome] = useState(null);
  const [outcomeLoading, setOutcomeLoading] = useState(false);
  const [outcomeError, setOutcomeError] = useState("");
  const [amountRecovered, setAmountRecovered] = useState("");

  const [auditEvents, setAuditEvents] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState("");

  const [recentEvents, setRecentEvents] = useState([]);

  const [backendOnline, setBackendOnline] = useState(false);
  const [newCaseOpen, setNewCaseOpen] = useState(false);
  const [paymentId, setPaymentId] = useState("");
  const [newCaseLoading, setNewCaseLoading] = useState(false);
  const [newCaseError, setNewCaseError] = useState("");

  useEffect(() => {
    getRecoveryCases()
      .then((cases) => {
        setRecoveryCases(cases);
        setRecoveryCase(cases[0] ?? null);
      })
      .catch((error) => setCaseError(error.message))
      .finally(() => setCaseLoading(false));
  }, []);

  useEffect(() => {
    checkHealth()
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

  // Without this the Recovery Outcomes view only ever showed an outcome
  // recorded in this browser session, and was empty after a reload.
  const selectedCaseId = recoveryCase?.case_id;

  useEffect(() => {
    if (!selectedCaseId) return;

    // Switching cases before the request lands would otherwise show the
    // previous case's outcome against the new one.
    let cancelled = false;

    getRecoveryOutcomes(selectedCaseId)
      .then((outcomes) => {
        if (!cancelled) setRecoveryOutcome(outcomes.at(-1) ?? null);
      })
      .catch(() => {
        if (!cancelled) setRecoveryOutcome(null);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedCaseId]);

  // Refetched whenever a step lands, so the feed reflects the workflow
  // being driven from this page rather than only the state at page load.
  // Keyed on the identifiers rather than the objects: re-fetching a case
  // hands back an equal-but-new object, which would refetch for nothing.
  const auditKey = [
    riskAssessment?.assessment_id,
    recoveryAction?.action_id,
    recoveryAction?.status,
    recoveryOutcome?.outcome_id,
  ].join("|");

  useEffect(() => {
    getRecentAuditEvents()
      .then(setRecentEvents)
      .catch(() => setRecentEvents([]));
  }, [auditKey]);

  const amountValue =
    amountRecovered === ""
      ? (recoveryCase?.amount_at_risk ?? "")
      : amountRecovered;

  const displayedCases = useMemo(
    () =>
      recoveryCases.map((item) => {
        const label = CASE_STATUS_LABELS[item.status] ?? {
          text: item.status,
          tone: "neutral",
        };

        return {
          id: item.case_id,
          // The full identifier is a uuid; the tail is enough to tell
          // rows apart and the title attribute keeps the whole value.
          shortId: item.case_id.replace(/^case_/, "").slice(0, 8),
          customer: item.customer_id,
          amount: rupees(Number(item.amount_at_risk)),
          risk: riskBand(item.risk_score),
          status: label.text,
          tone: label.tone,
        };
      }),
    [recoveryCases]
  );

  const selectCase = (caseId) => {
    const selectedCase = recoveryCases.find(
      (currentCase) => currentCase.case_id === caseId
    );

    if (!selectedCase) return;

    setRecoveryCase(selectedCase);
    setAmountRecovered("");
    setRiskAssessment(null);
    setAiDecision(null);
    setRecoveryAction(null);
    setRecoveryOutcome(null);
  };

  const handleRiskAssessment = async () => {
    if (!recoveryCase) {
      setRiskError("Recovery case is not loaded yet.");
      return;
    }

    setRiskLoading(true);
    setRiskError("");

    try {
      const assessment = await createRiskAssessment(recoveryCase.case_id);
      setRiskAssessment(assessment);
    } catch (error) {
      setRiskError(error.message);
    } finally {
      setRiskLoading(false);
    }
  };

  const handleAIDecision = async () => {
    if (!recoveryCase) {
      setAiError("Recovery case is not loaded yet.");
      return;
    }

    setAiLoading(true);
    setAiError("");

    try {
      const decision = await createAIDecision(recoveryCase.case_id);
      setAiDecision(decision);
    } catch (error) {
      setAiError(error.message);
    } finally {
      setAiLoading(false);
    }
  };

  const handleAIRecoveryAction = async () => {
    if (!recoveryCase) {
      setActionError("Recovery case is not loaded yet.");
      return;
    }

    setActionLoading(true);
    setActionError("");

    try {
      const action = await createAIRecoveryAction(recoveryCase.case_id);
      setRecoveryAction(action);
    } catch (error) {
      setActionError(error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveAction = async () => {
    if (!recoveryAction) {
      setActionError("No recovery action is available.");
      return;
    }

    setActionLoading(true);
    setActionError("");

    try {
      const action = await approveRecoveryAction(
        recoveryAction.action_id
      );
      setRecoveryAction(action);
    } catch (error) {
      setActionError(error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartAction = async () => {
    if (!recoveryAction) {
      setActionError("No recovery action is available.");
      return;
    }

    setActionLoading(true);
    setActionError("");

    try {
      const action = await startRecoveryAction(
        recoveryAction.action_id
      );
      setRecoveryAction(action);
    } catch (error) {
      setActionError(error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteAction = async () => {
    if (!recoveryAction) {
      setActionError("No recovery action is available.");
      return;
    }

    setActionLoading(true);
    setActionError("");

    try {
      const action = await completeRecoveryAction(
        recoveryAction.action_id
      );
      setRecoveryAction(action);
    } catch (error) {
      setActionError(error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRecoveryOutcome = async (status) => {
    if (!recoveryCase || !recoveryAction) {
      setOutcomeError("Recovery case or action is not available.");
      return;
    }

    // Nothing is recovered when the attempt failed, and a partial
    // recovery is whatever the operator entered. Sending the full amount
    // at risk for every outcome recorded revenue that never came back.
    const amount =
      status === "not_recovered"
        ? "0.00"
        : status === "recovered"
          ? recoveryCase.amount_at_risk
          : amountValue;

    if (status === "partially_recovered") {
      const entered = Number(amount);

      if (!Number.isFinite(entered) || entered <= 0) {
        setOutcomeError("Enter the amount recovered.");
        return;
      }

      if (entered >= Number(recoveryCase.amount_at_risk)) {
        setOutcomeError(
          "A partial recovery must be less than the amount at risk."
        );
        return;
      }
    }

    setOutcomeLoading(true);
    setOutcomeError("");

    try {
      const outcome = await recordRecoveryOutcome(
        recoveryCase.case_id,
        recoveryAction.action_id,
        status,
        amount
      );

      // The case status is not the outcome status: a failed recovery
      // leaves the case "failed", not "not_recovered".
      const caseStatus =
        outcome.status === "not_recovered" ? "failed" : outcome.status;

      setRecoveryOutcome(outcome);
      setRecoveryCase((currentCase) =>
        currentCase ? { ...currentCase, status: caseStatus } : currentCase
      );
      setRecoveryCases((cases) =>
        cases.map((item) =>
          item.case_id === recoveryCase.case_id
            ? { ...item, status: caseStatus }
            : item
        )
      );
    } catch (error) {
      setOutcomeError(error.message);
    } finally {
      setOutcomeLoading(false);
    }
  };

  const handleAuditEvents = async () => {
    setAuditLoading(true);
    setAuditError("");

    try {
      let currentCase = recoveryCase;

      if (!currentCase) {
        currentCase = await getRecoveryCase(
          "case_8b2527b3ef6944cd905867838da21a01"
        );

        setRecoveryCase(currentCase);
      }

      const events = await getAuditEvents(currentCase.case_id);
      setAuditEvents(events);
    } catch (error) {
      setAuditError(error.message);
    } finally {
      setAuditLoading(false);
    }
  };

  const handleCreateRecoveryCase = async (event) => {
    event.preventDefault();
    if (!paymentId.trim()) {
      setNewCaseError("Enter a payment ID to create a recovery case.");
      return;
    }

    setNewCaseLoading(true);
    setNewCaseError("");

    try {
      const createdCase = await createRecoveryCase(paymentId.trim());
      setRecoveryCases((currentCases) => [createdCase, ...currentCases]);
      setRecoveryCase(createdCase);
      setPaymentId("");
      setNewCaseOpen(false);
    } catch (error) {
      setNewCaseError(error.message);
    } finally {
      setNewCaseLoading(false);
    }
  };

  const riskLabel = riskAssessment
    ? riskAssessment.risk_score >= 60
      ? "High"
      : riskAssessment.risk_score >= 30
        ? "Medium"
        : "Low"
    : "Pending";

  const riskTone =
    riskLabel === "High"
      ? "danger"
      : riskLabel === "Medium"
        ? "warning"
        : riskLabel === "Low"
          ? "success"
          : "primary";

  return (
    <div className="app-shell">
      {newCaseOpen && (
        <div className="modal-backdrop">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="new-case-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">RECOVERY PIPELINE</p>
                <h3 id="new-case-title">New Recovery Case</h3>
              </div>
              <button
                className="icon-button"
                onClick={() => setNewCaseOpen(false)}
                aria-label="Close new recovery case form"
              >
                <X size={19} />
              </button>
            </div>

            <form onSubmit={handleCreateRecoveryCase}>
              <label className="form-label" htmlFor="payment-id">Payment ID</label>
              <input
                id="payment-id"
                className="form-input"
                value={paymentId}
                onChange={(event) => setPaymentId(event.target.value)}
                placeholder="Enter an existing payment ID"
                autoFocus
              />
              {newCaseError && <div className="error-message">{newCaseError}</div>}
              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setNewCaseOpen(false)}
                >
                  Cancel
                </button>
                <button className="primary-button" type="submit" disabled={newCaseLoading}>
                  {newCaseLoading ? "Creating..." : "Create Case"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {sidebarOpen && (
        <button
          className="mobile-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation"
        />
      )}

      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-header">
          <div className="brand-mark">
          </div>

          <div className="brand-copy">
            <strong>RecoverAI</strong>
            <span>Revenue Intelligence</span>
          </div>

          <button
            className="close-sidebar"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="navigation">
          <p className="nav-label">WORKSPACE</p>

          <button
            className={`nav-item ${activeView === "dashboard" ? "active" : ""
              }`}
            onClick={() => {
              setActiveView("dashboard");
              setSidebarOpen(false);
            }}
          >
            <LayoutDashboard size={19} />
            Dashboard
          </button>

          <button
            className={`nav-item ${activeView === "cases" ? "active" : ""
              }`}
            onClick={() => {
              setActiveView("cases");
              setSidebarOpen(false);
            }}
          >
            <CreditCard size={19} />
            Recovery Cases
          </button>

          <button
            className={`nav-item ${activeView === "risk" ? "active" : ""
              }`}
            onClick={() => {
              setActiveView("risk");
              setSidebarOpen(false);
              handleRiskAssessment();
            }}
          >
            <ShieldCheck size={19} />
            Risk Assessment
          </button>

          <button
            className={`nav-item ${activeView === "ai-decisions" ? "active" : ""
              }`}
            onClick={() => {
              setActiveView("ai-decisions");
              setSidebarOpen(false);
              handleAIDecision();
            }}
          >
            AI Decisions
          </button>

          <button
            className={`nav-item ${activeView === "actions" ? "active" : ""
              }`}
            onClick={() => {
              setActiveView("actions");
              setSidebarOpen(false);
              handleAIRecoveryAction();
            }}
          >
            <Zap size={19} />
            Recovery Actions
          </button>

          <p className="nav-label nav-label-spaced">MONITORING</p>

          <button
            className={`nav-item ${activeView === "outcomes" ? "active" : ""}`}
            onClick={() => {
              setActiveView("outcomes");
              setSidebarOpen(false);
            }}
          >
            <CheckCircle2 size={19} />
            Recovery Outcomes
          </button>

          <button
            className={`nav-item ${activeView === "audit" ? "active" : ""}`}
            onClick={() => {
              setActiveView("audit");
              setSidebarOpen(false);
              handleAuditEvents();
            }}
          >
            <Clock3 size={19} />
            Audit Events
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="ai-status">
            <span className={`status-dot ${backendOnline ? "" : "offline"}`} />
            <div>
              <strong>
                {backendOnline ? "AI Engine Online" : "AI Engine Offline"}
              </strong>
              <span>
                {backendOnline
                  ? "Backend connected"
                  : "Backend unavailable"}
              </span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button
            className="menu-button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={21} />
          </button>

          <div className="breadcrumb">
            <span>Workspace</span>
            <span>/</span>
            <strong>
              {activeView === "cases"
                ? "Recovery Cases"
                : activeView === "risk"
                  ? "Risk Assessment"
                  : activeView === "ai-decisions"
                    ? "AI Decisions"
                    : activeView === "actions"
                      ? "Recovery Actions"
                      : activeView === "outcomes"
                        ? "Recovery Outcomes"
                        : activeView === "audit"
                          ? "Audit Events"
                          : "Dashboard"}
            </strong>
          </div>

          <div className="topbar-right">
            <span className="live-indicator">
              <span className="status-dot" />
              Live
            </span>
            <div className="avatar">N</div>
          </div>
        </header>

        <div className="content">
          {activeView === "cases" ? (
            <>
              <section className="page-heading">
                <div>
                  <p className="eyebrow">RECOVERY PIPELINE</p>
                  <h2>Recovery Cases</h2>
                  <p>
                    Review failed payments and manage AI-powered recovery
                    actions.
                  </p>
                </div>

                <button
                  className="primary-button"
                  onClick={() => {
                    setNewCaseError("");
                    setNewCaseOpen(true);
                  }}
                >
                  New Recovery Case
                </button>
              </section>

              <section className="stats-grid">
                <article className="stat-card">
                  <div className="stat-icon warning">
                    <CreditCard size={20} />
                  </div>
                  <div className="stat-content">
                    <span>Total Cases</span>
                    <strong>{displayedCases.length}</strong>
                    <small>Active recovery pipeline</small>
                  </div>
                </article>

                <article className="stat-card">
                  <div className="stat-icon primary">
                    <ShieldCheck size={20} />
                  </div>
                  <div className="stat-content">
                    <span>High Risk</span>
                    <strong>
                      {
                        displayedCases.filter((item) =>
                          item.risk.text.startsWith("High")
                        ).length
                      }
                    </strong>
                    <small>Require attention</small>
                  </div>
                </article>

                <article className="stat-card">
                  <div className="stat-icon success">
                    <Target size={20} />
                  </div>
                  <div className="stat-content">
                    <span>Recoverable</span>
                    <strong>
                      {summary.recoverability === null
                        ? "—"
                        : `${summary.recoverability}%`}
                    </strong>
                    <small>
                      {summary.recoverability === null
                        ? "No cases assessed yet"
                        : `Mean of ${summary.assessedCount} assessed`}
                    </small>
                  </div>
                </article>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">ACTIVE CASES</p>
                    <h3>Recovery Pipeline</h3>
                  </div>
                  <ArrowUpRight size={19} />
                </div>

                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Case</th>
                        <th>Customer</th>
                        <th>Amount</th>
                        <th>Risk</th>
                        <th>Status</th>
                      </tr>
                    </thead>

                    <tbody>
                      {displayedCases.map((item) => (
                        <tr
                          key={item.id}
                          className="case-row"
                          tabIndex={0}
                          role="button"
                          aria-label={`Open recovery case for ${item.customer}, ${item.amount}`}
                          onClick={() => selectCase(item.id)}
                          onKeyDown={(event) => {
                            // A row is not a button, so Enter and Space have
                            // to be wired up for it to be usable without a
                            // mouse at all.
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              selectCase(item.id);
                            }
                          }}
                        >
                          <td>
                            <code className="case-id" title={item.id}>
                              {item.shortId}
                            </code>
                          </td>
                          <td>{item.customer}</td>
                          <td className="numeric">{item.amount}</td>
                          <td>
                            <span
                              className={`risk-badge ${item.risk.tone}`}
                            >
                              {item.risk.text}
                            </span>
                          </td>
                          <td>
                            <span className={`case-status ${item.tone}`}>
                              {item.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          ) : activeView === "risk" ? (
            <>
              <section className="page-heading">
                <div>
                  <p className="eyebrow">RISK INTELLIGENCE</p>
                  <h2>Risk Assessment</h2>
                  <p>
                    Evaluate payment risk and recoverability using the
                    recovery engine.
                  </p>
                </div>

                <button
                  className="primary-button"
                  onClick={handleRiskAssessment}
                  disabled={riskLoading}
                >
                  <ShieldCheck size={17} />
                  {riskLoading ? "Assessing..." : "Run Assessment"}
                </button>
              </section>

              {riskError && (
                <div className="error-message">{riskError}</div>
              )}

              <section className="stats-grid">
                <article className="stat-card">
                  <div className={`stat-icon ${riskTone}`}>
                    <ShieldCheck size={20} />
                  </div>
                  <div className="stat-content">
                    <span>Risk Score</span>
                    <strong>
                      {riskAssessment
                        ? `${riskAssessment.risk_score}`
                        : "—"}
                    </strong>
                    <small>{riskLabel} risk</small>
                  </div>
                </article>

                <article className="stat-card">
                  <div className="stat-icon success">
                    <Target size={20} />
                  </div>
                  <div className="stat-content">
                    <span>Recoverability</span>
                    <strong>
                      {riskAssessment
                        ? `${riskAssessment.recoverability_score}`
                        : "—"}
                    </strong>
                    <small>Out of 100</small>
                  </div>
                </article>

                <article className="stat-card">
                  <div className="stat-icon warning">
                    <CreditCard size={20} />
                  </div>
                  <div className="stat-content">
                    <span>Amount at Risk</span>
                    <strong>
                      {riskAssessment
                        ? `₹${Number(
                          riskAssessment.amount_at_risk
                        ).toLocaleString("en-IN")}`
                        : "—"}
                    </strong>
                    <small>Current recovery case</small>
                  </div>
                </article>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">ASSESSMENT RESULT</p>
                    <h3>Risk Analysis</h3>
                  </div>
                  <ShieldCheck size={19} />
                </div>

                {riskAssessment ? (
                  <div className="assessment-result">
                    <div>
                      <span className="result-label">Risk Level</span>
                      <span
                        className={`risk-badge ${riskLabel.toLowerCase()}`}
                      >
                        {riskLabel}
                      </span>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Reason</span>
                      <p>{riskAssessment.reason}</p>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Assessment ID</span>
                      <p>{riskAssessment.assessment_id}</p>
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">
                    <ShieldCheck size={30} />
                    <h3>No assessment yet</h3>
                    <p>
                      Click “Run Assessment” to evaluate this recovery
                      case.
                    </p>
                  </div>
                )}
              </section>
            </>
          ) : activeView === "ai-decisions" ? (
            <>
              <section className="page-heading">
                <div>
                  <p className="eyebrow">AI RECOVERY ENGINE</p>
                  <h2>AI Decisions</h2>
                  <p>
                    Generate a bounded recovery recommendation from the
                    latest risk assessment.
                  </p>
                </div>

                <button
                  className="primary-button"
                  onClick={handleAIDecision}
                  disabled={aiLoading}
                >
                  {aiLoading ? "Generating..." : "Generate AI Decision"}
                </button>
              </section>

              {aiError && (
                <div className="error-message">{aiError}</div>
              )}

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">RECOMMENDATION</p>
                    <h3>Recovery Decision</h3>
                  </div>
                </div>

                {aiDecision ? (
                  <div className="assessment-result">
                    <div>
                      <span className="result-label">
                        Recommended Action
                      </span>
                      <strong className="decision-value">
                        {aiDecision.recommended_action}
                      </strong>
                    </div>

                    <div>
                      <span className="result-label">Confidence</span>
                      <span className="risk-badge medium">
                        {aiDecision.confidence}
                      </span>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Rationale</span>
                      <p>{aiDecision.rationale}</p>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Decision ID</span>
                      <p>{aiDecision.decision_id}</p>
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">
                    <h3>No AI decision yet</h3>
                    <p>
                      Generate an AI decision for the current recovery
                      case.
                    </p>
                  </div>
                )}
              </section>
            </>
          ) : activeView === "actions" ? (
            <>
              <section className="page-heading">
                <div>
                  <p className="eyebrow">RECOVERY EXECUTION</p>
                  <h2>Recovery Actions</h2>
                  <p>
                    Convert the AI recommendation into a controlled recovery
                    action.
                  </p>
                </div>

                <button
                  className="primary-button"
                  onClick={handleAIRecoveryAction}
                  disabled={actionLoading}
                >
                  <Zap size={17} />
                  {actionLoading
                    ? "Creating..."
                    : "Create AI Action"}
                </button>
              </section>

              {actionError && (
                <div className="error-message">{actionError}</div>
              )}

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">ACTION CONTROL</p>
                    <h3>Recovery Action</h3>
                  </div>
                  <Zap size={19} />
                </div>

                {recoveryAction ? (
                  <div className="assessment-result">
                    <div>
                      <span className="result-label">Action Type</span>
                      <strong className="decision-value">
                        {recoveryAction.action_type}
                      </strong>
                    </div>

                    <div>
                      <span className="result-label">Status</span>
                      <span className="case-status">
                        {recoveryAction.status}
                      </span>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Action ID</span>
                      <p>{recoveryAction.action_id}</p>
                    </div>

                    {recoveryAction.status === "proposed" && (
                      <button
                        className="primary-button"
                        onClick={handleApproveAction}
                        disabled={actionLoading}
                      >
                        <CheckCircle2 size={17} />
                        {actionLoading
                          ? "Approving..."
                          : "Approve Action"}
                      </button>
                    )}

                    {recoveryAction.status === "approved" && (
                      <button
                        className="primary-button"
                        onClick={handleStartAction}
                        disabled={actionLoading}
                      >
                        <Zap size={17} />
                        {actionLoading
                          ? "Starting..."
                          : "Start Action"}
                      </button>
                    )}

                    {recoveryAction.status === "executing" && (
                      <button
                        className="primary-button"
                        onClick={handleCompleteAction}
                        disabled={actionLoading}
                      >
                        <CheckCircle2 size={17} />
                        {actionLoading
                          ? "Completing..."
                          : "Complete Action"}
                      </button>
                    )}

                    {recoveryAction.status === "completed" && (
                      <div className="outcome-controls">
                        <span className="result-label">Record Outcome</span>

                        <label className="outcome-amount">
                          Amount recovered
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            max={recoveryCase?.amount_at_risk}
                            value={amountValue}
                            onChange={(event) =>
                              setAmountRecovered(event.target.value)
                            }
                            disabled={outcomeLoading}
                          />
                        </label>

                        <div className="outcome-buttons">
                          <button
                            className="primary-button"
                            onClick={() => handleRecoveryOutcome("recovered")}
                            disabled={outcomeLoading}
                          >
                            <CheckCircle2 size={17} />
                            {outcomeLoading
                              ? "Recording..."
                              : "Mark Recovered"}
                          </button>

                          <button
                            className="secondary-button"
                            onClick={() =>
                              handleRecoveryOutcome("partially_recovered")
                            }
                            disabled={outcomeLoading}
                          >
                            Mark Partially Recovered
                          </button>

                          <button
                            className="secondary-button"
                            onClick={() =>
                              handleRecoveryOutcome("not_recovered")
                            }
                            disabled={outcomeLoading}
                          >
                            Mark Not Recovered
                          </button>
                        </div>
                      </div>
                    )}

                    {outcomeError && (
                      <div className="error-message">{outcomeError}</div>
                    )}

                    {recoveryOutcome && (
                      <div className="result-block">
                        <span className="result-label">Outcome Recorded</span>
                        <p>
                          {recoveryOutcome.status} — ₹
                          {Number(
                            recoveryOutcome.amount_recovered
                          ).toLocaleString("en-IN")}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="empty-state">
                    <Zap size={30} />
                    <h3>No recovery action yet</h3>
                    <p>
                      Create an AI recovery action for the current case.
                    </p>
                  </div>
                )}
              </section>
            </>
          ) : activeView === "outcomes" ? (
            <>
              <section className="page-heading">
                <div>
                  <p className="eyebrow">RECOVERY MONITORING</p>
                  <h2>Recovery Outcomes</h2>
                  <p>
                    Track the result of executed recovery actions and recovered
                    revenue.
                  </p>
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">OUTCOME STATUS</p>
                    <h3>Recovery Outcome</h3>
                  </div>
                  <CheckCircle2 size={19} />
                </div>

                {recoveryOutcome ? (
                  <div className="assessment-result">
                    <div>
                      <span className="result-label">Status</span>
                      <span className="case-status">
                        {recoveryOutcome.status}
                      </span>
                    </div>

                    <div>
                      <span className="result-label">Amount Recovered</span>
                      <strong className="decision-value">
                        ₹
                        {Number(
                          recoveryOutcome.amount_recovered
                        ).toLocaleString("en-IN")}
                      </strong>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Outcome ID</span>
                      <p>{recoveryOutcome.outcome_id}</p>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Case ID</span>
                      <p>{recoveryOutcome.case_id}</p>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Action ID</span>
                      <p>{recoveryOutcome.action_id}</p>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Recorded At</span>
                      <p>{recoveryOutcome.recorded_at}</p>
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">
                    <CheckCircle2 size={30} />
                    <h3>No recovery outcome recorded</h3>
                    <p>
                      Complete a recovery action and record its outcome to see
                      the result here.
                    </p>
                  </div>
                )}
              </section>
            </>
          ) : activeView === "audit" ? (
            <>
              <section className="page-heading">
                <div>
                  <p className="eyebrow">SYSTEM MONITORING</p>
                  <h2>Audit Events</h2>
                  <p>
                    Review the complete audit trail of recovery actions for
                    the current recovery case.
                  </p>
                </div>

                <button
                  className="secondary-button"
                  onClick={handleAuditEvents}
                  disabled={auditLoading}
                >
                  <RefreshCw size={17} />
                  {auditLoading ? "Refreshing..." : "Refresh Events"}
                </button>
              </section>

              {auditError && (
                <div className="error-message">{auditError}</div>
              )}

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">AUDIT TRAIL</p>
                    <h3>Recovery Activity</h3>
                  </div>
                  <Clock3 size={19} />
                </div>

                {auditLoading ? (
                  <div className="empty-state">
                    <Clock3 size={30} />
                    <h3>Loading audit events...</h3>
                    <p>
                      Retrieving the recovery case audit trail.
                    </p>
                  </div>
                ) : auditEvents.length > 0 ? (
                  <div className="audit-events">
                    {auditEvents.map((event) => (
                      <div className="audit-event" key={event.event_id}>
                        <div className="audit-event-icon">
                          <Clock3 size={17} />
                        </div>

                        <div className="audit-event-content">
                          <div className="audit-event-header">
                            <strong>{event.event_type}</strong>
                            <span>{event.occurred_at}</span>
                          </div>

                          <p>{event.reason}</p>

                          <div className="audit-event-meta">
                            <span>
                              <strong>Actor:</strong> {event.actor}
                            </span>
                            <span>
                              <strong>Event ID:</strong> {event.event_id}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <Clock3 size={30} />
                    <h3>No audit events found</h3>
                    <p>
                      No audit activity has been recorded for this recovery
                      case yet.
                    </p>
                  </div>
                )}
              </section>
            </>
          ) : (
            <>
              <section className="page-heading">
                <div>
                  <p className="eyebrow">RECOVERY INTELLIGENCE</p>
                  <h2>Revenue Recovery Dashboard</h2>

                  <p>
                    Monitor failed payments, AI decisions, and recovered
                    revenue in one place.
                  </p>
                </div>

                <button
                  className="primary-button"
                  onClick={() => setActiveView("ai-decisions")}
                >
                  AI Recovery Overview
                </button>
              </section>

              <section className="stats-grid">
                {stats.map((stat) => {
                  const Icon = stat.icon;

                  return (
                    <article className="stat-card" key={stat.label}>
                      <div className={`stat-icon ${stat.tone}`}>
                        <Icon size={20} />
                      </div>

                      <div className="stat-content">
                        <span>{stat.label}</span>
                        <strong>{stat.value}</strong>
                        <small>{stat.detail}</small>
                      </div>
                    </article>
                  );
                })}
              </section>

              <section className="panel progress-panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">RECOVERY PROGRESS</p>
                    <h3>Recovered against revenue at risk</h3>
                  </div>
                  <span className="progress-rate">{summary.rate}%</span>
                </div>

                <div
                  className="meter"
                  role="img"
                  aria-label={`${rupees(summary.recovered)} recovered of ${rupees(
                    summary.atRisk
                  )} at risk`}
                >
                  <div
                    className="meter-fill"
                    style={{ width: `${summary.rate}%` }}
                  />
                </div>

                <div className="meter-legend">
                  <span>
                    <strong>{rupees(summary.recovered)}</strong> recovered
                  </span>
                  <span>
                    <strong>{rupees(summary.outstanding)}</strong> outstanding
                  </span>
                </div>

                {summary.pipeline.length > 0 && (
                  <>
                    <p className="progress-subhead">Cases by outcome</p>

                    <div className="pipeline-bar">
                      {summary.pipeline.map((bucket) => (
                        <span
                          key={bucket.key}
                          className="pipeline-segment"
                          style={{
                            flexGrow: bucket.count,
                            background: bucket.color,
                          }}
                          title={`${bucket.label}: ${bucket.count}`}
                        />
                      ))}
                    </div>

                    <ul className="pipeline-legend">
                      {summary.pipeline.map((bucket) => (
                        <li key={bucket.key}>
                          <span
                            className="legend-swatch"
                            style={{ background: bucket.color }}
                          />
                          {bucket.label}
                          <strong>{bucket.count}</strong>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </section>

              <section className="dashboard-grid">
                <article className="panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">RECOVERY PIPELINE</p>
                      <h3>Recent Recovery Cases</h3>
                    </div>

                    <button
                      className="icon-button"
                      onClick={() => setActiveView("cases")}
                    >
                      <ArrowUpRight size={19} />
                    </button>
                  </div>

                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Case</th>
                          <th>Customer</th>
                          <th>Amount</th>
                          <th>Risk</th>
                          <th>Status</th>
                        </tr>
                      </thead>

                      <tbody>
                        {displayedCases.slice(0, 5).map((item) => (
                          <tr key={item.id}>
                            <td>
                              <code className="case-id" title={item.id}>
                                {item.shortId}
                              </code>
                            </td>
                            <td>{item.customer}</td>
                            <td className="numeric">{item.amount}</td>
                            <td>
                              <span
                                className={`risk-badge ${item.risk.tone}`}
                              >
                                {item.risk.text}
                              </span>
                            </td>
                            <td>
                              <span className={`case-status ${item.tone}`}>
                                {item.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>

                <article className="panel activity-panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">LIVE ACTIVITY</p>
                      <h3>Recent Events</h3>
                    </div>

                    <Clock3 size={19} />
                  </div>

                  <div className="activity-list">
                    {recentEvents.length === 0 && (
                      <p className="activity-empty">
                        No recovery activity yet. Run a recovery action to
                        see events appear here.
                      </p>
                    )}

                    {recentEvents.map((event) => {
                      const label = EVENT_LABELS[event.event_type] ?? {
                        title: event.event_type,
                        icon: Zap,
                      };
                      const Icon = label.icon;

                      return (
                        <div className="activity-item" key={event.event_id}>
                          <div className="activity-icon">
                            <Icon size={17} />
                          </div>

                          <div className="activity-copy">
                            <strong>{label.title}</strong>
                            <span>{event.reason}</span>
                            <small>{relativeTime(event.occurred_at)}</small>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </article>
              </section>

              {caseLoading && (
                <div className="loading-message">
                  Loading recovery case...
                </div>
              )}

              {caseError && (
                <div className="error-message">{caseError}</div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;