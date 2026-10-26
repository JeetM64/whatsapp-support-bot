"use strict";

const metricsRoot = document.querySelector("#metrics");
const emptyState = document.querySelector("#empty-state");
let metricsData = null;

function setText(selector, value) {
  document.querySelector(selector).textContent = value === null || value === undefined ? "Not available" : String(value);
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function drawBars(selector, rows, labelField = "label", showRate = false) {
  const container = document.querySelector(selector);
  clear(container);
  const data = Array.isArray(rows) ? rows : Object.entries(rows || {}).map(([label, count]) => ({ label, count }));
  if (!data.length) { container.append(Object.assign(document.createElement("p"), { textContent: "No data" })); return; }
  const max = Math.max(1, ...data.map(row => Number(row.count) || 0));
  for (const row of data) {
    const line = document.createElement("div");
    line.className = "bar-row";
    const label = document.createElement("span");
    label.className = "bar-label";
    label.textContent = String(row[labelField] ?? "Unknown");
    const track = document.createElement("div");
    track.className = "bar-track";
    const bar = document.createElement("span");
    bar.className = "bar-fill";
    const amount = Math.max(0, Number(row.count) || 0);
    const steppedWidth = Math.min(100, Math.max(0, Math.round((amount / max * 100) / 5) * 5));
    bar.classList.add(`bar-w-${steppedWidth}`);
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `${label.textContent}: ${amount}`);
    track.append(bar);
    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = showRate ? `${amount} · ${Number(row.rate_percent) || 0}%` : String(amount);
    line.append(label, track, value);
    container.append(line);
  }
}

function updateHours() {
  if (!metricsData) return;
  if (metricsData.auto_resolved_percent === null || metricsData.auto_resolved_percent === undefined) {
    setText("#hours-saved", "Not available yet");
    return;
  }
  const minutes = Number(document.querySelector("#minutes-per-message").value);
  const handled = Number(metricsData.messages_handled) || 0;
  const rate = Number(metricsData.auto_resolved_percent) || 0;
  const hours = handled * rate / 100 * (Number.isFinite(minutes) ? minutes : 0) / 60;
  setText("#hours-saved", `${hours.toFixed(2)} hours`);
}

async function load() {
  const response = await fetch("/api/metrics/public");
  if (!response.ok) throw new Error("Aggregate metrics could not be loaded.");
  metricsData = await response.json();
  document.querySelector("#demo-label").hidden = metricsData.demo_data !== true;
  const hasData = Number(metricsData.messages_handled) > 0 || Number(metricsData.sla_breaches) > 0 || (metricsData.top_intents || []).length > 0;
  emptyState.hidden = hasData;
  metricsRoot.hidden = !hasData;
  if (!hasData) return;
  setText("#messages-count", metricsData.messages_handled);
  setText("#auto-rate", metricsData.auto_resolved_percent === null ? "Not available" : `${metricsData.auto_resolved_percent}%`);
  setText("#latency", metricsData.average_bot_latency_ms === null ? "Not available" : `${metricsData.average_bot_latency_ms} ms`);
  setText("#sla-breaches", metricsData.sla_breaches);
  setText("#token-cost", metricsData.token_cost_per_1000_messages_usd === null ? "Not available" : `$${metricsData.token_cost_per_1000_messages_usd}`);
  setText("#token-cost-note", metricsData.token_cost_status === "no_llm_mode" ? "0 in no-LLM mode" : metricsData.token_cost_status === "token_logs" ? "Calculated from logged token usage" : "Token cost logs are not available");
  drawBars("#reasons-chart", metricsData.escalations_by_reason, "label", true);
  drawBars("#priority-chart", metricsData.escalations_by_priority, "label", true);
  drawBars("#intents-chart", metricsData.top_intents);
  drawBars("#gaps-chart", metricsData.kb_gaps, "topic");
  drawBars("#language-chart", metricsData.language_split);
  drawBars("#batch-chart", metricsData.batch_type_split);
  updateHours();
}

document.querySelector("#minutes-per-message").addEventListener("input", updateHours);
load().catch(error => { const node = document.querySelector("#load-error"); node.textContent = error.message; node.hidden = false; });
