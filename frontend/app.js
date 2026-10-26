"use strict";

const SUGGESTIONS = [
  "How do I enroll?",
  "iCAT syllabus kya hai",
  "Will I get a certificate?",
  "payment cut gaya par access nahi aaya",
  "refund milega?",
  "Are certificates AICTE approved?"
];
const GREETING_EN = "Hi, I'm the iStudio support assistant. I can help with iCAT, fees, certificates, refunds and your training or internship dashboard. What do you need?";
const GREETING_HI = "Namaste, main iStudio support assistant hoon. Main iCAT, fees, certificates, refunds aur aapke training ya internship dashboard mein madad kar sakta hoon. Aapko kya chahiye?";

const messages = document.querySelector("#messages");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const typing = document.querySelector("#typing");
const handoff = document.querySelector("#handoff");
const handoffCopy = document.querySelector("#handoff-copy");
const optionSection = document.querySelector("#quick-replies");
const optionChips = document.querySelector("#option-chips");
const debugPanel = document.querySelector("#debug-panel");
const debugFields = document.querySelector("#debug-fields");
const debugToggle = document.querySelector("#debug-toggle");

function newSenderId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") return `web-${window.crypto.randomUUID()}`;
  const values = new Uint32Array(4);
  window.crypto.getRandomValues(values);
  return `web-${Array.from(values, value => value.toString(16)).join("")}`;
}

function senderId() {
  let value = sessionStorage.getItem("istudio-web-sender");
  if (!value) {
    value = newSenderId();
    sessionStorage.setItem("istudio-web-sender", value);
  }
  return value;
}

function safeHelpUrl(value) {
  try {
    const url = new URL(String(value));
    if (url.protocol !== "https:") return null;
    if (!["internshipstudio.com", "internshipstudio.tawk.help"].includes(url.hostname.toLowerCase())) return null;
    return url.href;
  } catch (_) {
    return null;
  }
}

function addBubble(text, who, metadata = {}) {
  const article = document.createElement("article");
  article.classList.add("bubble", who);
  const paragraph = document.createElement("p");
  paragraph.textContent = String(text);
  article.append(paragraph);
  if (who === "assistant" && metadata.source_status) {
    const badge = document.createElement("small");
    badge.className = "source-badge";
    badge.textContent = metadata.source_status === "verified" ? "From iStudio help center" : "Some details pending confirmation";
    article.append(badge);
    const helpUrl = safeHelpUrl(metadata.help_link);
    if (helpUrl) {
      const link = document.createElement("a");
      link.className = "help-link";
      link.href = helpUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Help center";
      article.append(link);
    }
  }
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function hinglishMessage(value) {
  return /[\u0900-\u097f]|\b(kya|hai|ka|ki|ke|mujhe|mera|meri|kitni|kitna|milega|chahiye|paise|paisa|ho gaya|nahi|nahin|batao|karu|karun|kaise)\b/i.test(value);
}

function setGreeting(language = "en") {
  clearChildren(messages);
  const article = document.createElement("article");
  article.className = "bubble assistant";
  article.dataset.greeting = "true";
  const paragraph = document.createElement("p");
  paragraph.textContent = language === "hi" ? GREETING_HI : GREETING_EN;
  article.append(paragraph);
  messages.append(article);
}

function clearChildren(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function showOptions(options) {
  clearChildren(optionChips);
  const choices = Array.isArray(options) ? options.filter(value => typeof value === "string" && value.trim()) : [];
  optionSection.hidden = choices.length === 0;
  for (const choice of choices) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip";
    button.textContent = choice;
    button.addEventListener("click", () => sendMessage(choice));
    optionChips.append(button);
  }
}

function showDebug(debug) {
  clearChildren(debugFields);
  const fields = [
    ["Decision", debug.decision],
    ["Reason code", debug.reason_code],
    ["KB ids", Array.isArray(debug.kb_ids) ? debug.kb_ids.join(", ") : ""],
    ["Confidence", typeof debug.confidence === "number" ? debug.confidence.toFixed(3) : debug.confidence],
    ["Mode", debug.mode],
    ["Source status", debug.source_status],
    ["Help link", debug.help_link]
  ];
  for (const [label, value] of fields) {
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value === undefined || value === null ? "Not available" : String(value);
    debugFields.append(term, detail);
  }
}

function showHandoff(ticket) {
  if (!ticket || typeof ticket.ticket_id !== "string") {
    handoff.hidden = true;
    return;
  }
  const eta = typeof ticket.sla_deadline === "string" && ticket.sla_deadline ? ticket.sla_deadline : "the next support update";
  handoffCopy.textContent = `Ticket ${ticket.ticket_id}. We aim to reply by ${eta}.`;
  handoff.hidden = false;
}

async function sendMessage(value) {
  const text = String(value || "").trim();
  if (!text) return;
  if (messages.querySelector("[data-greeting='true']")) setGreeting(hinglishMessage(text) ? "hi" : "en");
  addBubble(text, "user");
  input.value = "";
  typing.hidden = false;
  showOptions([]);
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: senderId(), text })
    });
    const payload = await response.json();
    if (!response.ok) throw new Error("The message could not be sent. Please try again.");
    const metadata = { source_status: payload.source_status, help_link: payload.help_link };
    for (const message of Array.isArray(payload.messages) ? payload.messages : []) addBubble(message, "assistant", metadata);
    showOptions(payload.options);
    showHandoff(payload.ticket);
    showDebug(payload.debug || {});
  } catch (error) {
    addBubble(error instanceof Error ? error.message : "The message could not be sent. Please try again.", "assistant");
  } finally {
    typing.hidden = true;
    input.focus();
  }
}

for (const suggestion of SUGGESTIONS) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "chip";
  button.textContent = suggestion;
  button.addEventListener("click", () => sendMessage(suggestion));
  document.querySelector("#try-chips").append(button);
}

form.addEventListener("submit", event => {
  event.preventDefault();
  sendMessage(input.value);
});

debugToggle.addEventListener("click", () => {
  const opening = debugPanel.hidden;
  debugPanel.hidden = !opening;
  debugToggle.setAttribute("aria-expanded", String(opening));
});

document.querySelector("#new-chat").addEventListener("click", () => {
  sessionStorage.setItem("istudio-web-sender", newSenderId());
  setGreeting("en");
  showOptions([]);
  showHandoff(null);
  clearChildren(debugFields);
  debugPanel.hidden = true;
  debugToggle.setAttribute("aria-expanded", "false");
  input.value = "";
  input.focus();
});
