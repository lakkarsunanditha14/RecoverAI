import {
  AlertTriangle,
  ArrowUpRight,
  Check,
  CheckCircle2,
  Clock3,
  CreditCard,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  X,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  approveRecoveryAction,
  recordRecoveryOutcome,
  runRecoveryAgent,
  runRecoveryBatch,
  startRecoveryAction,
  completeRecoveryAction,
  checkHealth,
  createAIDecision,
  createAIRecoveryAction,
  createRecoveryCase,
  createRiskAssessment,
  getRecoveryCase,
  getRecoveryCases,
  getRecoveryPolicy,
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
      value: rupees(atRisk),
      detail: `Total potential exposure`,
      icon: AlertTriangle,
      tone: "danger",
    },
    {
      label: "Revenue Recovered",
      value: rupees(recovered),
      detail: `Total successfully collected`,
      icon: Target,
      tone: "success",
    },
    {
      label: "Outstanding Revenue",
      value: rupees(outstanding),
      detail: `${openCount} open ${openCount === 1 ? "case" : "cases"} pending`,
      icon: Clock3,
      tone: "warning",
    },
    {
      label: "Recovery Rate",
      value: `${rate}%`,
      detail: `${closedCount} of ${summary.total} cases closed`,
      icon: RefreshCw,
      tone: "primary",
    },
  ];
}

function ActiveCaseBanner({ recoveryCase }) {
  if (!recoveryCase) {
    return (
      <div className="active-case-banner empty">
        <div className="banner-details">
          <AlertTriangle size={18} style={{ color: "var(--warning)" }} />
          <span>No recovery case selected. Select a case from the Recovery Cases view.</span>
        </div>
      </div>
    );
  }

  const label = CASE_STATUS_LABELS[recoveryCase.status] ?? {
    text: recoveryCase.status,
    tone: "neutral",
  };
  const risk = riskBand(recoveryCase.risk_score);

  return (
    <div className="active-case-banner">
      <div className="banner-details">
        <div className="banner-item">
          <label>Active Case</label>
          <span>
            <code className="case-id-code">
              {recoveryCase.case_id.replace(/^case_/, "").slice(0, 8)}
            </code>
          </span>
        </div>
        <div className="banner-item">
          <label>Customer</label>
          <span>{recoveryCase.customer_id}</span>
        </div>
        <div className="banner-item">
          <label>Amount at Risk</label>
          <span className="banner-amount">
            {rupees(Number(recoveryCase.amount_at_risk))}
          </span>
        </div>
        <div className="banner-item">
          <label>Risk Level</label>
          <span className={`risk-badge ${risk.tone}`}>{risk.text}</span>
        </div>
        <div className="banner-item">
          <label>Status</label>
          <span className={`case-status ${label.tone}`}>{label.text}</span>
        </div>
      </div>
    </div>
  );
}

function WorkflowStepper({
  activeView,
  setActiveView,
  riskAssessment,
  aiDecision,
  recoveryAction,
  recoveryOutcome,
}) {
  const steps = [
    {
      id: "risk",
      title: "1. Risk Assessment",
      subtitle: riskAssessment ? `Score: ${riskAssessment.risk_score}` : "Pending assessment",
      isComplete: !!riskAssessment,
      isCurrent: activeView === "risk",
    },
    {
      id: "ai-decisions",
      title: "2. AI Decision",
      subtitle: aiDecision ? aiDecision.recommended_action : "Pending decision",
      isComplete: !!aiDecision,
      isCurrent: activeView === "ai-decisions",
    },
    {
      id: "actions",
      title: "3. Recovery Action",
      subtitle: recoveryAction ? recoveryAction.status : "Pending action",
      isComplete: !!recoveryAction && (recoveryAction.status === "completed" || recoveryAction.status === "executing" || recoveryAction.status === "approved"),
      isCurrent: activeView === "actions",
    },
    {
      id: "outcomes",
      title: "4. Outcome & Audit",
      subtitle: recoveryOutcome ? recoveryOutcome.status : "Pending outcome",
      isComplete: !!recoveryOutcome,
      isCurrent: activeView === "outcomes" || activeView === "audit",
    },
  ];

  return (
    <div className="workflow-stepper">
      {steps.map((step, idx) => (
        <div key={step.id} className="stepper-item-wrapper">
          <div
            className={`workflow-step ${step.isComplete ? "completed" : ""} ${step.isCurrent ? "current" : ""}`}
            onClick={() => setActiveView(step.id)}
            role="button"
            tabIndex={0}
          >
            <div className="step-number">
              {step.isComplete ? <Check size={14} /> : idx + 1}
            </div>
            <div className="step-info">
              <span className="step-title">{step.title}</span>
              <span className="step-status">{step.subtitle}</span>
            </div>
          </div>
          {idx < steps.length - 1 && (
            <div className={`step-connector ${step.isComplete ? "filled" : ""}`} />
          )}
        </div>
      ))}
    </div>
  );
}

const formatEnumLabel = (str) => {
  if (!str) return "—";
  return str
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

function NextBestAction({
  recoveryCase,
  riskAssessment,
  aiDecision,
  recoveryAction,
  recoveryOutcome,
  setActiveView,
  handleRiskAssessment,
  handleAIDecision,
  handleApproveAction,
  handleStartAction,
  handleCompleteAction,
  actionLoading,
  riskLoading,
  aiLoading,
}) {
  if (!recoveryCase) return null;

  let description = "";
  let actionButton = null;
  let isDone = false;

  if (!riskAssessment) {
    description = "Run the risk assessment for this recovery case.";
    actionButton = (
      <button
        className="primary-button"
        onClick={handleRiskAssessment}
        disabled={riskLoading}
      >
        <ShieldCheck size={16} />
        {riskLoading ? "Assessing..." : "Run Assessment"}
      </button>
    );
  } else if (!aiDecision) {
    description = "Generate the AI recovery decision.";
    actionButton = (
      <button
        className="primary-button"
        onClick={() => {
          setActiveView("ai-decisions");
          handleAIDecision();
        }}
        disabled={aiLoading}
      >
        <Sparkles size={16} />
        {aiLoading ? "Generating..." : "Generate AI Decision"}
      </button>
    );
  } else if (!recoveryAction) {
    description = "Create the AI recovery action.";
    actionButton = (
      <button
        className="primary-button"
        onClick={() => setActiveView("actions")}
      >
        <Zap size={16} />
        Go to Actions
      </button>
    );
  } else if (recoveryAction.status === "proposed") {
    description = "Approve the proposed recovery action.";
    actionButton = (
      <button
        className="primary-button"
        onClick={() => {
          setActiveView("actions");
          handleApproveAction();
        }}
        disabled={actionLoading}
      >
        <CheckCircle2 size={16} />
        {actionLoading ? "Approving..." : "Approve Action"}
      </button>
    );
  } else if (recoveryAction.status === "approved") {
    description = "Start the approved recovery action.";
    actionButton = (
      <button
        className="primary-button"
        onClick={() => {
          setActiveView("actions");
          handleStartAction();
        }}
        disabled={actionLoading}
      >
        <Zap size={16} />
        {actionLoading ? "Starting..." : "Start Action"}
      </button>
    );
  } else if (recoveryAction.status === "executing") {
    description = "Complete the executing recovery action.";
    actionButton = (
      <button
        className="primary-button"
        onClick={() => {
          setActiveView("actions");
          handleCompleteAction();
        }}
        disabled={actionLoading}
      >
        <CheckCircle2 size={16} />
        {actionLoading ? "Completing..." : "Complete Action"}
      </button>
    );
  } else if (recoveryAction.status === "completed" && !recoveryOutcome) {
    description = "Record the recovery outcome for this case.";
    actionButton = (
      <button
        className="primary-button"
        onClick={() => setActiveView("actions")}
      >
        <CheckCircle2 size={16} />
        Record Outcome
      </button>
    );
  } else {
    description = "Recovery case workflow completed.";
    isDone = true;
  }

  return (
    <div className="next-best-action-card">
      <div className="nba-content">
        <div className="nba-badge">
          <Sparkles size={14} />
          <span>NEXT BEST ACTION</span>
        </div>
        <p className="nba-desc">{description}</p>
      </div>
      <div className="nba-cta">
        {isDone ? (
          <span className="case-status success">
            <Check size={14} /> Completed
          </span>
        ) : (
          actionButton
        )}
      </div>
    </div>
  );
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
  decision_generated: { title: "AI decision generated", icon: Sparkles },
  action_authorized: { title: "Action authorized by policy", icon: ShieldCheck },
  payment_verified: { title: "Payment verified", icon: CheckCircle2 },
  retry_attempted: { title: "Retry attempted", icon: RefreshCw },
  retry_limit_reached: { title: "Retry limit reached", icon: AlertTriangle },
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

function formatTimestamp(isoString) {
  // The value comes from the database; this only formats it. Same UTC
  // correction as relativeTime, since the backend stores naive UTC and
  // JavaScript would otherwise read it as local time.
  const at = new Date(
    isoString.endsWith("Z") ? isoString : `${isoString}Z`
  );

  return at.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
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

  const [agentRunning, setAgentRunning] = useState(false);
  const [agentResult, setAgentResult] = useState(null);
  const [agentError, setAgentError] = useState("");

  const [batchRunning, setBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState(null);
  const [batchResult, setBatchResult] = useState(null);

  const [policy, setPolicy] = useState(null);

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

  useEffect(() => {
    getRecoveryPolicy()
      .then(setPolicy)
      .catch(() => setPolicy(null));
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

  const [searchQuery, setSearchQuery] = useState("");

  const filteredCases = useMemo(() => {
    if (!searchQuery.trim()) return displayedCases;
    const query = searchQuery.toLowerCase().trim();
    return displayedCases.filter(
      (item) =>
        item.shortId.toLowerCase().includes(query) ||
        item.customer.toLowerCase().includes(query) ||
        item.status.toLowerCase().includes(query) ||
        item.id.toLowerCase().includes(query)
    );
  }, [displayedCases, searchQuery]);

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

  const handleRunAgent = async () => {
    if (!recoveryCase) {
      setAgentError("Select a recovery case first.");
      return;
    }

    setAgentRunning(true);
    setAgentError("");

    try {
      const result = await runRecoveryAgent(recoveryCase.case_id);
      setAgentResult(result);

      // The run changes case status and recovered amounts, so the
      // dashboard is re-read rather than patched from the response.
      const cases = await getRecoveryCases();
      setRecoveryCases(cases);
      setRecoveryCase(
        cases.find((item) => item.case_id === recoveryCase.case_id) ?? null
      );
    } catch (error) {
      setAgentError(error.message);
    } finally {
      setAgentRunning(false);
    }
  };

  const handleRunBatch = async () => {
    setBatchRunning(true);
    setBatchProgress({ processed: 0, remaining: null });

    try {
      let processed = 0;

      // Each request handles a few cases so none of them runs past the
      // host's request timeout; loop until the backend reports nothing
      // left to do.
      for (let round = 0; round < 40; round += 1) {
        const result = await runRecoveryBatch(3);
        processed += result.cases_processed;

        setBatchProgress({ processed, remaining: result.cases_remaining });
        setBatchResult(result);

        if (result.cases_remaining === 0 || result.cases_processed === 0) {
          break;
        }
      }

      setRecoveryCases(await getRecoveryCases());
    } catch (error) {
      setAgentError(error.message);
    } finally {
      setBatchRunning(false);
    }
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
            <Sparkles size={19} />
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
            <div className="header-system-status">
              <span className="system-badge">
                <span className="pulse-dot" />
                SYSTEM OPERATIONAL
              </span>
              <span className="api-badge">
                <span className="pulse-dot" />
                API CONNECTED
              </span>
            </div>
            <div className="avatar">N</div>
          </div>
        </header>

        <div className="content view-fade-in" key={activeView}>
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

                <div className="heading-actions">
                  <button
                    className="primary-button"
                    onClick={handleRunAgent}
                    disabled={agentRunning || !recoveryCase}
                  >
                    <Zap size={17} />
                    {agentRunning ? "Running agent…" : "Run Recovery Agent"}
                  </button>

                  <button
                    className="secondary-button"
                    onClick={() => {
                      setNewCaseError("");
                      setNewCaseOpen(true);
                    }}
                  >
                    New Recovery Case
                  </button>
                </div>
              </section>

              {agentError && (
                <div className="error-message">{agentError}</div>
              )}

              {agentResult && (
                <section className="panel agent-result">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">AGENT RUN</p>
                      <h3>
                        {agentResult.escalated
                          ? "Escalated for human review"
                          : agentResult.amount_recovered > 0
                            ? "Recovered"
                            : "Stopped"}
                      </h3>
                    </div>

                    <span
                      className={`case-status ${agentResult.escalated
                        ? "danger"
                        : agentResult.amount_recovered > 0
                          ? "success"
                          : "neutral"
                        }`}
                    >
                      {agentResult.status}
                    </span>
                  </div>

                  <dl className="agent-stats">
                    <div>
                      <dt>Policy decision</dt>
                      <dd>{agentResult.policy_decision}</dd>
                    </div>
                    <div>
                      <dt>Attempts used</dt>
                      <dd>
                        {agentResult.attempt_number} of{" "}
                        {agentResult.max_attempts}
                      </dd>
                    </div>
                    <div>
                      <dt>Risk / recoverability</dt>
                      <dd>
                        {agentResult.risk_score.toFixed(0)} /{" "}
                        {agentResult.recoverability_score.toFixed(0)}
                      </dd>
                    </div>
                    <div>
                      <dt>Amount recovered</dt>
                      <dd>{rupees(agentResult.amount_recovered)}</dd>
                    </div>
                    <div>
                      <dt>Stop reason</dt>
                      <dd>{agentResult.stop_reason || "—"}</dd>
                    </div>
                    <div>
                      <dt>Audit events written</dt>
                      <dd>{agentResult.audit_event_ids.length}</dd>
                    </div>
                  </dl>

                  <p className="simulation-note">
                    Test Simulation — no payment provider is contacted.
                  </p>
                </section>
              )}
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

                <div className="table-header-controls">
                  <div className="table-search-bar">
                    <Search size={16} className="search-icon" />
                    <input
                      type="text"
                      placeholder="Filter cases by ID, customer, status..."
                      value={searchQuery}
                      onChange={(event) => setSearchQuery(event.target.value)}
                      className="table-search-input"
                    />
                    {searchQuery && (
                      <button
                        className="clear-search"
                        onClick={() => setSearchQuery("")}
                        aria-label="Clear search filter"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>
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
                      {filteredCases.map((item) => (
                        <tr
                          key={item.id}
                          className={`case-row ${item.id === selectedCaseId ? "selected" : ""}`}
                          tabIndex={0}
                          role="button"
                          aria-label={`Open recovery case for ${item.customer}, ${item.amount}`}
                          onClick={() => selectCase(item.id)}
                          onKeyDown={(event) => {
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

              <ActiveCaseBanner recoveryCase={recoveryCase} />
              <WorkflowStepper
                activeView={activeView}
                setActiveView={setActiveView}
                riskAssessment={riskAssessment}
                aiDecision={aiDecision}
                recoveryAction={recoveryAction}
                recoveryOutcome={recoveryOutcome}
              />
              <NextBestAction
                recoveryCase={recoveryCase}
                riskAssessment={riskAssessment}
                aiDecision={aiDecision}
                recoveryAction={recoveryAction}
                recoveryOutcome={recoveryOutcome}
                setActiveView={setActiveView}
                handleRiskAssessment={handleRiskAssessment}
                handleAIDecision={handleAIDecision}
                handleApproveAction={handleApproveAction}
                handleStartAction={handleStartAction}
                handleCompleteAction={handleCompleteAction}
                actionLoading={actionLoading}
                riskLoading={riskLoading}
                aiLoading={aiLoading}
              />

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
                  <Sparkles size={17} />
                  {aiLoading ? "Generating..." : "Generate AI Decision"}
                </button>
              </section>

              <ActiveCaseBanner recoveryCase={recoveryCase} />
              <WorkflowStepper
                activeView={activeView}
                setActiveView={setActiveView}
                riskAssessment={riskAssessment}
                aiDecision={aiDecision}
                recoveryAction={recoveryAction}
                recoveryOutcome={recoveryOutcome}
              />
              <NextBestAction
                recoveryCase={recoveryCase}
                riskAssessment={riskAssessment}
                aiDecision={aiDecision}
                recoveryAction={recoveryAction}
                recoveryOutcome={recoveryOutcome}
                setActiveView={setActiveView}
                handleRiskAssessment={handleRiskAssessment}
                handleAIDecision={handleAIDecision}
                handleApproveAction={handleApproveAction}
                handleStartAction={handleStartAction}
                handleCompleteAction={handleCompleteAction}
                actionLoading={actionLoading}
                riskLoading={riskLoading}
                aiLoading={aiLoading}
              />

              {aiError && (
                <div className="error-message">{aiError}</div>
              )}

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">RECOMMENDATION</p>
                    <h3>AI Recovery Decision</h3>
                  </div>
                  {aiDecision ? (
                    <span className="case-status success" style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                      <CheckCircle2 size={13} /> DECISION READY
                    </span>
                  ) : (
                    <span className="case-status warning">PENDING</span>
                  )}
                </div>

                {aiDecision ? (
                  <div className="assessment-result">
                    <div>
                      <span className="result-label">
                        Recommended Recovery Action
                      </span>
                      <strong className="decision-value" style={{ fontSize: "18px", color: "var(--primary)" }}>
                        {formatEnumLabel(aiDecision.recommended_action)}
                      </strong>
                    </div>

                    <div className="confidence-meter-container">
                      <div className="confidence-header">
                        <span className="result-label" style={{ margin: 0 }}>Decision Confidence</span>
                        <span className="risk-badge medium">
                          {formatEnumLabel(aiDecision.confidence)} (
                          {String(aiDecision.confidence).toLowerCase() === "high"
                            ? "87%"
                            : String(aiDecision.confidence).toLowerCase() === "medium"
                            ? "65%"
                            : "45%"}
                          )
                        </span>
                      </div>
                      <div className="confidence-meter-bar">
                        <div
                          className="confidence-meter-fill"
                          style={{
                            width:
                              String(aiDecision.confidence).toLowerCase() === "high"
                                ? "87%"
                                : String(aiDecision.confidence).toLowerCase() === "medium"
                                ? "65%"
                                : "45%",
                          }}
                        />
                      </div>
                    </div>

                    <div className="result-block">
                      <span className="result-label">AI Rationale</span>
                      <p>{aiDecision.rationale}</p>
                    </div>

                    <div className="why-checklist">
                      <p className="why-title">WHY THIS ACTION</p>
                      <ul className="why-list">
                        <li><CheckCircle2 size={15} /> Evaluated recoverability profile & failure cause</li>
                        <li><CheckCircle2 size={15} /> Validated within max retries & recovery window policy</li>
                        <li><CheckCircle2 size={15} /> High probability of successful collection with minimal customer friction</li>
                      </ul>
                    </div>

                    <div className="result-block">
                      <span className="result-label">Decision ID</span>
                      <p><code>{aiDecision.decision_id}</code></p>
                    </div>
                  </div>
                ) : (
                  <div className="ai-pending-panel">
                    <div className="panel-header">
                      <div>
                        <p className="eyebrow">AI RECOVERY RECOMMENDATION</p>
                        <h3>AI Decision Pending</h3>
                      </div>
                      <span className="case-status warning">Pending</span>
                    </div>

                    <p className="pending-desc">
                      No recovery decision has been generated yet.
                    </p>

                    <div className="eval-checklist">
                      <p className="checklist-title">The Recovery AI will evaluate:</p>
                      <ul>
                        <li><CheckCircle2 size={15} /> Risk assessment</li>
                        <li><CheckCircle2 size={15} /> Recoverability score</li>
                        <li><CheckCircle2 size={15} /> Amount at risk</li>
                        <li><CheckCircle2 size={15} /> Recovery policy and guardrails</li>
                      </ul>
                    </div>

                    <div className="pending-actions">
                      <button
                        className="primary-button"
                        onClick={handleAIDecision}
                        disabled={aiLoading}
                      >
                        <Sparkles size={17} />
                        {aiLoading ? "Generating..." : "Generate AI Decision"}
                      </button>
                    </div>
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

              <ActiveCaseBanner recoveryCase={recoveryCase} />
              <WorkflowStepper
                activeView={activeView}
                setActiveView={setActiveView}
                riskAssessment={riskAssessment}
                aiDecision={aiDecision}
                recoveryAction={recoveryAction}
                recoveryOutcome={recoveryOutcome}
              />

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
                        {formatEnumLabel(recoveryAction.action_type)}
                      </strong>
                    </div>

                    <div style={{ marginTop: "16px" }}>
                      <span className="result-label">Status</span>
                      <span className="case-status">
                        {formatEnumLabel(recoveryAction.status)}
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

              <ActiveCaseBanner recoveryCase={recoveryCase} />
              <WorkflowStepper
                activeView={activeView}
                setActiveView={setActiveView}
                riskAssessment={riskAssessment}
                aiDecision={aiDecision}
                recoveryAction={recoveryAction}
                recoveryOutcome={recoveryOutcome}
              />
              <NextBestAction
                recoveryCase={recoveryCase}
                riskAssessment={riskAssessment}
                aiDecision={aiDecision}
                recoveryAction={recoveryAction}
                recoveryOutcome={recoveryOutcome}
                setActiveView={setActiveView}
                handleRiskAssessment={handleRiskAssessment}
                handleAIDecision={handleAIDecision}
                handleApproveAction={handleApproveAction}
                handleStartAction={handleStartAction}
                handleCompleteAction={handleCompleteAction}
                actionLoading={actionLoading}
                riskLoading={riskLoading}
                aiLoading={aiLoading}
              />

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
                      <span className="case-status success">
                        {formatEnumLabel(recoveryOutcome.status)}
                      </span>
                    </div>

                    <div style={{ marginTop: "16px" }}>
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
                      <p>{formatTimestamp(recoveryOutcome.recorded_at)}</p>
                    </div>
                  </div>
                ) : (
                  <div className="outcome-pending-panel">
                    <div className="panel-header">
                      <div>
                        <p className="eyebrow">RECOVERY OUTCOME</p>
                        <h3>Awaiting recovery execution</h3>
                      </div>
                      <span className="case-status warning">Awaiting Execution</span>
                    </div>

                    <p className="pending-desc">
                      The recovery action must be completed before an outcome can be recorded.
                    </p>

                    <div className="workflow-checklist">
                      <p className="checklist-title">Workflow Progress:</p>
                      <ul className="workflow-status-list">
                        <li className={riskAssessment ? "done" : "pending"}>
                          {riskAssessment ? <CheckCircle2 size={16} /> : <span className="circle-icon">○</span>} Risk Assessment
                        </li>
                        <li className={aiDecision ? "done" : "pending"}>
                          {aiDecision ? <CheckCircle2 size={16} /> : <span className="circle-icon">○</span>} AI Decision
                        </li>
                        <li className={recoveryAction && recoveryAction.status === "completed" ? "done" : "pending"}>
                          {recoveryAction && recoveryAction.status === "completed" ? <CheckCircle2 size={16} /> : <span className="circle-icon">○</span>} Recovery Action Execution
                        </li>
                        <li className={recoveryOutcome ? "done" : "pending"}>
                          {recoveryOutcome ? <CheckCircle2 size={16} /> : <span className="circle-icon">○</span>} Outcome Recording
                        </li>
                      </ul>
                    </div>

                    <div className="pending-actions">
                      <button
                        className="primary-button"
                        onClick={() => setActiveView("actions")}
                      >
                        <Zap size={17} />
                        Go to Recovery Actions
                      </button>
                    </div>
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

              <ActiveCaseBanner recoveryCase={recoveryCase} />
              <WorkflowStepper
                activeView={activeView}
                setActiveView={setActiveView}
                riskAssessment={riskAssessment}
                aiDecision={aiDecision}
                recoveryAction={recoveryAction}
                recoveryOutcome={recoveryOutcome}
              />

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
                    {auditEvents.map((event, index) => {
                      const label = EVENT_LABELS[event.event_type] ?? {
                        title: event.event_type,
                        icon: Clock3,
                      };
                      const Icon = label.icon;

                      return (
                        <div className="audit-event" key={event.event_id}>
                          <div className="audit-event-icon">
                            <Icon size={17} />
                          </div>

                          <div className="audit-event-content">
                            <div className="audit-event-header">
                              <strong>
                                <span className="audit-step">
                                  {index + 1}
                                </span>
                                {label.title}
                              </strong>
                              <span title={event.occurred_at}>
                                {formatTimestamp(event.occurred_at)}
                              </span>
                            </div>

                            <p>{event.reason}</p>

                            <div className="audit-event-meta">
                              <span>
                                <strong>Actor:</strong> {event.actor}
                              </span>
                              <span>
                                <strong>Type:</strong>{" "}
                                <code>{event.event_type}</code>
                              </span>
                              <span>
                                <strong>Case:</strong>{" "}
                                <code>
                                  {event.case_id
                                    .replace(/^case_/, "")
                                    .slice(0, 8)}
                                </code>
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
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

                <div className="heading-actions">
                  <button
                    className="primary-button"
                    onClick={handleRunBatch}
                    disabled={batchRunning}
                  >
                    <Zap size={17} />
                    {batchRunning
                      ? `Running… ${batchProgress?.processed ?? 0} done`
                      : "Run Recovery Batch"}
                  </button>

                  <button
                    className="secondary-button"
                    onClick={() => setActiveView("ai-decisions")}
                  >
                    AI Recovery Overview
                  </button>
                </div>
              </section>

              <section className="stats-grid">
                {stats.map((stat) => {
                  const Icon = stat.icon;

                  return (
                    <article className={`stat-card tone-${stat.tone}`} key={stat.label}>
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

              <section className="dashboard-workflow-connector">
                <div className="dwc-step">
                  <ShieldCheck size={16} style={{ color: "var(--primary)" }} />
                  <span>Risk Assessment</span>
                </div>
                <ArrowUpRight size={14} className="dwc-arrow" />
                <div className="dwc-step">
                  <Sparkles size={16} style={{ color: "var(--primary)" }} />
                  <span>AI Decision</span>
                </div>
                <ArrowUpRight size={14} className="dwc-arrow" />
                <div className="dwc-step">
                  <Zap size={16} style={{ color: "var(--primary)" }} />
                  <span>Recovery Action</span>
                </div>
                <ArrowUpRight size={14} className="dwc-arrow" />
                <div className="dwc-step">
                  <CheckCircle2 size={16} style={{ color: "var(--success)" }} />
                  <span>Outcome & Revenue</span>
                </div>
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

              <section className="agent-grid">
                <article className="panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">AI RECOVERY AGENT</p>
                      <h3>Agent Activity</h3>
                    </div>
                    <span className="agent-state">
                      <span className="status-dot" />
                      {batchRunning ? "RUNNING" : "ACTIVE"}
                    </span>
                  </div>

                  <dl className="agent-stats">
                    <div>
                      <dt>Cases processed</dt>
                      <dd>{batchProgress?.processed ?? 0}</dd>
                    </div>
                    <div>
                      <dt>Payments recovered</dt>
                      <dd>{batchResult?.recovered_cases ?? summary.closedCount}</dd>
                    </div>
                    <div>
                      <dt>Cases escalated</dt>
                      <dd>{batchResult?.escalated_cases ?? 0}</dd>
                    </div>
                    <div>
                      <dt>Cases still open</dt>
                      <dd>{batchResult?.cases_remaining ?? summary.openCount}</dd>
                    </div>
                  </dl>

                  <p className="simulation-note">
                    Test Simulation — no payment provider is contacted.
                  </p>
                </article>

                <article className="panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">BOUNDED AUTOMATION</p>
                      <h3>Recovery Guardrails</h3>
                    </div>
                    <ShieldCheck size={19} />
                  </div>

                  <dl className="guardrails">
                    <div>
                      <dt>Max retries</dt>
                      <dd>{policy?.max_retries ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Recovery window</dt>
                      <dd>
                        {policy ? `${policy.recovery_window_days} days` : "—"}
                      </dd>
                    </div>
                    <div>
                      <dt>Stop on success</dt>
                      <dd>{policy?.stop_on_success ? "On" : "—"}</dd>
                    </div>
                    <div>
                      <dt>High risk</dt>
                      <dd>
                        {policy
                          ? `Human review at ${policy.high_risk_threshold}`
                          : "—"}
                      </dd>
                    </div>
                    <div>
                      <dt>High value</dt>
                      <dd>
                        {policy
                          ? `Policy review at ${rupees(
                            policy.high_value_threshold
                          )}`
                          : "—"}
                      </dd>
                    </div>
                  </dl>
                </article>
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