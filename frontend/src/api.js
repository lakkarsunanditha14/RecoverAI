const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `API request failed (${response.status}): ${errorText}`
    );
  }

  return response.json();
}

export async function checkHealth() {
  return apiRequest("/health");
}

export async function getRecoveryCases() {
  return apiRequest("/recovery-cases");
}

export async function getRecoveryCase(caseId) {
  return apiRequest(`/recovery-cases/${caseId}`);
}

export async function createRecoveryCase(paymentId) {
  return apiRequest(`/recovery-cases/${paymentId}`, {
    method: "POST",
  });
}

export async function createRiskAssessment(caseId) {
  return apiRequest(`/recovery-cases/${caseId}/risk-assessments`, {
    method: "POST",
  });
}

export async function createAIDecision(caseId) {
  return apiRequest(`/recovery-cases/${caseId}/decisions/ai`, {
    method: "POST",
  });
}

export async function createAIRecoveryAction(caseId) {
  return apiRequest(`/recovery-cases/${caseId}/ai-action`, {
    method: "POST",
  });
}

export async function approveRecoveryAction(actionId) {
  return apiRequest(`/recovery-actions/${actionId}/approve`, {
    method: "POST",
  });
}

export async function startRecoveryAction(actionId) {
  return apiRequest(`/recovery-actions/${actionId}/start`, {
    method: "POST",
  });
}

export async function completeRecoveryAction(actionId) {
  return apiRequest(`/recovery-actions/${actionId}/complete`, {
    method: "POST",
  });
}

export async function failRecoveryAction(actionId) {
  return apiRequest(`/recovery-actions/${actionId}/fail`, {
    method: "POST",
  });
}

export async function recordRecoveryOutcome(
  caseId,
  actionId,
  status,
  amountRecovered
) {
  return apiRequest(`/recovery-cases/${caseId}/outcomes`, {
    method: "POST",
    body: JSON.stringify({
      action_id: actionId,
      status,
      amount_recovered: amountRecovered,
    }),
  });
}

export async function getAuditEvents(caseId) {
  return apiRequest(`/recovery-cases/${caseId}/audit-events`);
}