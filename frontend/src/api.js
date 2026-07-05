/**
 * api.js — Centralized API client for the Leave Management Agent frontend.
 * All backend communication goes through these functions.
 */

// Backend URL
const API_BASE = "https://leave-management-agent.onrender.com/api";

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const config = {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  };

  const response = await fetch(url, config);

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong");
  }

  return data;
}

// ── Auth ──────────────────────────────────────────────────────────
export const login = (username, password) =>
  request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

// ── Employee ──────────────────────────────────────────────────────
export const getEmployee = (id) => request(`/employees/${id}`);

export const getBalances = (id) =>
  request(`/employees/${id}/balances`);

// ── Leave Requests ────────────────────────────────────────────────
export const applyLeave = (data) =>
  request("/leave/apply", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getRequests = (employeeId) =>
  request(`/leave/requests/${employeeId}`);

export const cancelLeave = (requestId) =>
  request(`/leave/cancel/${requestId}`, {
    method: "POST",
  });

// ── Manager ───────────────────────────────────────────────────────
export const getPendingRequests = (managerId) =>
  request(`/manager/${managerId}/pending`);

export const reviewRequest = (
  requestId,
  action,
  comment,
  managerId
) =>
  request(`/leave/review/${requestId}`, {
    method: "POST",
    body: JSON.stringify({
      action,
      comment,
      manager_id: managerId,
    }),
  });

// ── Team ──────────────────────────────────────────────────────────
export const getTeamCalendar = (teamId) =>
  request(`/team/${teamId}/calendar`);

// ── Chat ──────────────────────────────────────────────────────────
export const sendChatMessage = (message, employeeId) =>
  request("/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      employee_id: employeeId,
    }),
  });

export const confirmChatLeave = (data) =>
  request("/chat/confirm", {
    method: "POST",
    body: JSON.stringify(data),
  });

// ── Admin ─────────────────────────────────────────────────────────
export const getReports = () =>
  request("/admin/reports");

export const getAuditLog = () =>
  request("/admin/audit-log");

// ── Policies ──────────────────────────────────────────────────────
export const getPolicies = () =>
  request("/policies");