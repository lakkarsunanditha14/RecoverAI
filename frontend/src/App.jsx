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
import { useEffect, useState } from "react";
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
} from "./api";
import "./App.css";

const stats = [
  {
    label: "Revenue at Risk",
    value: "₹8.42L",
    change: "+12.4%",
    icon: AlertTriangle,
    tone: "danger",
  },
  {
    label: "Recoverable Amount",
    value: "₹6.18L",
    change: "73.3%",
    icon: Target,
    tone: "success",
  },
  {
    label: "Recovery Rate",
    value: "68.7%",
    change: "+8.2%",
    icon: RefreshCw,
    tone: "primary",
  },
  {
    label: "Failed Payments",
    value: "1,284",
    change: "-14.6%",
    icon: CreditCard,
    tone: "warning",
  },
];

const activities = [
  {
    title: "AI recovery action executed",
    description: "Smart retry initiated for RCV-10482",
    time: "2 min ago",
    icon: Zap,
  },
  {
    title: "Payment recovered",
    description: "₹72,000 successfully recovered",
    time: "18 min ago",
    icon: CheckCircle2,
  },
  {
    title: "Risk assessment completed",
    description: "RCV-10481 classified as medium risk",
    time: "31 min ago",
    icon: ShieldCheck,
  },
  {
    title: "Recovery reminder scheduled",
    description: "Customer reminder scheduled for tomorrow",
    time: "48 min ago",
    icon: Clock3,
  },
];

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");

  const [recoveryCases, setRecoveryCases] = useState([]);
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

  const [auditEvents, setAuditEvents] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState("");

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

  const displayedCases = recoveryCases.map((recoveryCase) => ({
    id: recoveryCase.case_id,
    customer: recoveryCase.customer_id,
    amount: `₹${Number(
      recoveryCase.amount_at_risk
    ).toLocaleString("en-IN")}`,
    risk:
      recoveryCase.status === "escalated"
        ? "High"
        : recoveryCase.status === "failed"
          ? "Medium"
          : recoveryCase.status === "recovered"
            ? "Low"
            : "Pending",
    decision:
      recoveryCase.status === "recovered"
        ? "Recovered"
        : recoveryCase.status === "escalated"
          ? "Escalate"
          : "Review",
    status:
      recoveryCase.status === "recovered"
        ? "Recovered"
        : recoveryCase.status === "escalated"
          ? "Pending Review"
          : "Action Required",
  }))

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

    setOutcomeLoading(true);
    setOutcomeError("");

    try {
      const outcome = await recordRecoveryOutcome(
        recoveryCase.case_id,
        recoveryAction.action_id,
        status,
        recoveryCase.amount_at_risk
      );

      setRecoveryOutcome(outcome);
      setRecoveryCase((currentCase) =>
        currentCase
          ? { ...currentCase, status: outcome.status === "recovered" ? "recovered" : currentCase.status }
          : currentCase
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
                        displayedCases.filter(
                          (item) => item.risk === "High"
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
                    <strong>73%</strong>
                    <small>Estimated recoverability</small>
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
                        <th>Decision</th>
                        <th>Status</th>
                      </tr>
                    </thead>

                    <tbody>
                      {displayedCases.map((item) => (
                        <tr
                          key={item.id}
                          className="case-row"
                          onClick={() => {
                            const selectedCase = recoveryCases.find(
                              (currentCase) => currentCase.case_id === item.id
                            );
                            if (selectedCase) {
                              setRecoveryCase(selectedCase);
                              setRiskAssessment(null);
                              setAiDecision(null);
                              setRecoveryAction(null);
                              setRecoveryOutcome(null);
                            }
                          }}
                        >
                          <td>{item.id}</td>
                          <td>{item.customer}</td>
                          <td>{item.amount}</td>
                          <td>
                            <span
                              className={`risk-badge ${item.risk.toLowerCase()}`}
                            >
                              {item.risk}
                            </span>
                          </td>
                          <td>{item.decision}</td>
                          <td>
                            <span className="case-status">
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
                        <small>{stat.change} vs last period</small>
                      </div>
                    </article>
                  );
                })}
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
                            <td>{item.id}</td>
                            <td>{item.customer}</td>
                            <td>{item.amount}</td>
                            <td>
                              <span
                                className={`risk-badge ${item.risk.toLowerCase()}`}
                              >
                                {item.risk}
                              </span>
                            </td>
                            <td>
                              <span className="case-status">
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
                    {activities.map((item) => {
                      const Icon = item.icon;

                      return (
                        <div
                          className="activity-item"
                          key={item.title}
                        >
                          <div className="activity-icon">
                            <Icon size={17} />
                          </div>

                          <div className="activity-copy">
                            <strong>{item.title}</strong>
                            <span>{item.description}</span>
                            <small>{item.time}</small>
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