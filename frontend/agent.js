"use strict";

let agentKey = "";
let tickets = [];
let selectedTicketId = "";
let currentTicket = null;

const gate = document.querySelector("#key-gate");
const inbox = document.querySelector("#inbox");
const keyInput = document.querySelector("#agent-key");
const keyError = document.querySelector("#key-error");
const inboxError = document.querySelector("#inbox-error");
const ticketList = document.querySelector("#ticket-list");
const detail = document.querySelector("#ticket-detail");

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${agentKey}`);
  if (options.body) headers.set("Content-Type", "application/json");
  return fetch(path, { ...options, headers });
}

async function signIn(key) {
  keyError.hidden = true;
  const response = await fetch("/api/agent/auth", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key })
  });
  if (!response.ok) throw new Error(response.status === 429 ? "Too many failed attempts. Wait five minutes and try again." : "That agent key was not accepted. No ticket data was loaded.");
  agentKey = key;
  await loadTickets();
  keyInput.value = "";
  gate.hidden = true;
  inbox.hidden = false;
}

async function loadTickets() {
  inboxError.hidden = true;
  const response = await request("/api/tickets");
  if (response.status === 401) {
    clearKey();
    throw new Error("Agent authorization expired. Enter the key again.");
  }
  if (!response.ok) throw new Error("Tickets could not be loaded.");
  tickets = await response.json();
  renderTicketList();
}

function ticketDeadline(value) {
  if (typeof value !== "string") return null;
  const match = value.match(/^\w+\s+(\d{1,2})\s+(\w+),\s+(\d{1,2}):(\d{2})\s+(AM|PM)\s+IST$/i);
  if (!match) return null;
  const months = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };
  const month = months[match[2].slice(0, 3)];
  if (month === undefined) return null;
  let hour = Number(match[3]) % 12;
  if (match[5].toUpperCase() === "PM") hour += 12;
  let year = new Date().getFullYear();
  let date = new Date(Date.UTC(year, month, Number(match[1]), hour - 5, Number(match[4]) - 30));
  if (date.getTime() - Date.now() > 300 * 86400000) date = new Date(Date.UTC(year - 1, month, Number(match[1]), hour - 5, Number(match[4]) - 30));
  return date;
}

function countdown(ticket) {
  if (ticket.status !== "open") return "Resolved";
  const deadline = ticketDeadline(ticket.sla_deadline);
  if (!deadline) return "SLA time unavailable";
  const remaining = deadline.getTime() - Date.now();
  const overdue = remaining < 0;
  const minutes = Math.floor(Math.abs(remaining) / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const value = days ? `${days}d ${hours % 24}h` : hours ? `${hours}h ${minutes % 60}m` : `${minutes}m`;
  return { text: overdue ? `Overdue by ${value}` : `${value} remaining`, overdue };
}

function renderTicketList() {
  while (ticketList.firstChild) ticketList.removeChild(ticketList.firstChild);
  const status = document.querySelector("#filter-status").value;
  const priority = document.querySelector("#filter-priority").value;
  const visible = tickets.filter(ticket => (status === "all" || ticket.status === status) && (priority === "all" || ticket.priority === priority));
  document.querySelector("#empty-tickets").hidden = visible.length !== 0;
  for (const ticket of visible) {
    const item = el("li", undefined, "ticket-item");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ticket-select";
    button.setAttribute("aria-current", String(ticket.ticket_id === selectedTicketId));
    const title = el("strong", `${ticket.ticket_id} · ${ticket.reason_code || "Support request"}`);
    const badges = el("span", undefined, "badges");
    badges.append(el("span", ticket.priority || "—", `badge priority-${String(ticket.priority || "").toLowerCase()}`));
    badges.append(el("span", ticket.status || "unknown", "badge"));
    if (ticket.demo === true) badges.append(el("span", "Demo", "badge demo-badge"));
    const time = countdown(ticket);
    const clock = el("span", typeof time === "string" ? time : time.text, `sla-countdown${typeof time === "object" && time.overdue ? " overdue" : ""}`);
    clock.dataset.ticketId = ticket.ticket_id;
    button.append(title, badges, clock);
    button.addEventListener("click", () => openTicket(ticket.ticket_id));
    item.append(button);
    ticketList.append(item);
  }
}

function detailLine(label, value) {
  const wrapper = el("div", undefined, "detail-line");
  wrapper.append(el("dt", label), el("dd", value === undefined || value === null || value === "" ? "Not available" : (Array.isArray(value) ? value.join(", ") : value)));
  return wrapper;
}

async function openTicket(ticketId) {
  inboxError.hidden = true;
  const response = await request(`/api/tickets/${encodeURIComponent(ticketId)}`);
  if (!response.ok) {
    inboxError.textContent = response.status === 401 ? "Agent authorization expired. Enter the key again." : "Ticket details could not be loaded.";
    inboxError.hidden = false;
    if (response.status === 401) clearKey();
    return;
  }
  currentTicket = await response.json();
  selectedTicketId = currentTicket.ticket_id;
  renderTicketList();
  renderDetail(currentTicket);
}

function renderDetail(ticket) {
  while (detail.firstChild) detail.removeChild(detail.firstChild);
  detail.append(el("h2", `Ticket ${ticket.ticket_id}`, "detail-title"));
  const fields = el("dl", undefined, "detail-grid");
  fields.append(detailLine("Reason code", ticket.reason_code), detailLine("Language", ticket.language), detailLine("Intent", ticket.intent), detailLine("KB ids tried", ticket.kb_ids_tried));
  detail.append(fields);
  detail.append(el("h3", "Summary"));
  const summary = el("ol", undefined, "summary-list");
  for (const line of (Array.isArray(ticket.summary_3_lines) ? ticket.summary_3_lines : []).slice(0, 3)) summary.append(el("li", line));
  detail.append(summary);
  detail.append(el("h3", "Masked transcript"));
  const transcript = el("ol", undefined, "transcript");
  for (const turn of Array.isArray(ticket.last_5_turns) ? ticket.last_5_turns : []) {
    const line = el("li", undefined, `transcript-${turn.role === "assistant" ? "assistant" : "customer"}`);
    line.append(el("strong", turn.role === "assistant" ? "Bot" : "Customer"), el("p", turn.text));
    transcript.append(line);
  }
  detail.append(transcript);
  detail.append(el("h3", "Suggested reply"));
  const reply = document.createElement("textarea");
  reply.id = "agent-reply";
  reply.maxLength = 600;
  reply.rows = 3;
  reply.setAttribute("aria-label", "Reply to customer");
  reply.value = ticket.suggested_reply || "";
  const actions = el("div", undefined, "ticket-actions");
  const fill = el("button", "Use suggested reply", "button secondary");
  fill.type = "button";
  fill.addEventListener("click", () => { reply.value = ticket.suggested_reply || ""; reply.focus(); });
  const send = el("button", "Send reply", "button primary");
  send.type = "button";
  send.disabled = ticket.status !== "open";
  send.addEventListener("click", () => sendReply(ticket.ticket_id, reply.value));
  const resolve = el("button", "Resolve ticket", "button secondary");
  resolve.type = "button";
  resolve.disabled = ticket.status !== "open";
  resolve.addEventListener("click", () => resolveTicket(ticket.ticket_id));
  actions.append(fill, send, resolve);
  detail.append(reply, actions);
  detail.append(el("p", "", "template-state"));
}

async function sendReply(ticketId, text) {
  const state = detail.querySelector(".template-state");
  const response = await request(`/api/tickets/${encodeURIComponent(ticketId)}/reply`, { method: "POST", body: JSON.stringify({ text }) });
  const result = await response.json();
  state.className = response.ok && result.needs_template ? "template-state needs-template" : "template-state";
  state.textContent = !response.ok ? "Reply could not be queued." : result.needs_template ? "Needs template: this reply requires an approved WhatsApp template because the 24-hour window has passed." : "Reply queued for the next customer message.";
}

async function resolveTicket(ticketId) {
  const response = await request(`/api/tickets/${encodeURIComponent(ticketId)}/resolve`, { method: "POST" });
  if (!response.ok) { inboxError.textContent = "Ticket could not be resolved."; inboxError.hidden = false; return; }
  await loadTickets();
  await openTicket(ticketId);
}

function clearKey() {
  agentKey = "";
  currentTicket = null;
  tickets = [];
  selectedTicketId = "";
  inbox.hidden = true;
  gate.hidden = false;
  keyInput.value = "";
  keyInput.focus();
}

document.querySelector("#key-form").addEventListener("submit", async event => {
  event.preventDefault();
  try { await signIn(keyInput.value); }
  catch (error) { agentKey = ""; keyInput.value = ""; keyError.textContent = error.message; keyError.hidden = false; }
});
document.querySelector("#refresh").addEventListener("click", () => loadTickets().catch(error => { inboxError.textContent = error.message; inboxError.hidden = false; }));
document.querySelector("#sign-out").addEventListener("click", clearKey);
document.querySelector("#filter-status").addEventListener("change", renderTicketList);
document.querySelector("#filter-priority").addEventListener("change", renderTicketList);
setInterval(() => { if (!inbox.hidden) renderTicketList(); }, 30000);
