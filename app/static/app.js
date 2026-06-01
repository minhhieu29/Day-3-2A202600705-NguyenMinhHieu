const HINTS = [
  "Khách phàn nàn gì về phòng và ăn sáng tại Sunrise Bay? Đưa trích dẫn. Đề xuất 2 ưu tiên cải thiện.",
  "Top 3 vấn đề lặp lại từ review tiêu cực là gì?",
  "Ăn sáng được đánh giá thế nào? Tóm tắt sentiment khía cạnh breakfast.",
  "Check-in chậm có phải vấn đề lặp lại không? Tìm review liên quan.",
];

const $ = (id) => document.getElementById(id);

function getMode() {
  const el = document.querySelector('input[name="mode"]:checked');
  return el ? el.value : "agent";
}

function formatCost(usd) {
  if (usd == null) return "—";
  if (usd < 0.01) return `$${usd.toFixed(6)}`;
  return `$${usd.toFixed(4)}`;
}

function formatTime() {
  return new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(text) {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
}

function renderBody(text) {
  const safe = escapeHtml(text);
  return safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
}

function appendMessage({ role, label, body, variant }) {
  const wrap = document.createElement("div");
  if (role === "user") {
    wrap.className = "msg msg-user";
    wrap.innerHTML = `<div class="msg-meta"><span class="msg-time">${formatTime()}</span></div>${renderBody(body)}`;
  } else if (role === "loading") {
    wrap.className = "msg msg-loading";
    wrap.id = "loadingBubble";
    wrap.textContent = body;
  } else if (role === "error") {
    wrap.className = "msg msg-error";
    wrap.innerHTML = renderBody(body);
  } else {
    wrap.className = `msg msg-assistant ${variant || ""}`;
    const badgeClass = variant === "chatbot" ? "badge-chatbot" : "badge-agent";
    wrap.innerHTML = `
      <div class="msg-meta">
        <span class="badge ${badgeClass}">${label}</span>
        <span class="msg-time">${formatTime()}</span>
      </div>
      ${renderBody(body)}`;
  }
  $("messages").appendChild(wrap);
  wrap.scrollIntoView({ behavior: "smooth", block: "end" });
  return wrap;
}

function removeLoading() {
  const el = document.getElementById("loadingBubble");
  if (el) el.remove();
}

function renderMetricsPanel(data, title) {
  const panel = $("metricsPanel");
  if (!data) {
    panel.innerHTML = '<p class="muted">Chưa có dữ liệu.</p>';
    return;
  }

  const rows = [
    ["Thời gian (wall)", `${data.latency_ms} ms`],
    ["LLM calls", data.llm_calls ?? "—"],
    ["Prompt tokens", data.prompt_tokens ?? 0],
    ["Completion tokens", data.completion_tokens ?? 0],
    ["Total tokens", data.total_tokens ?? 0],
    ["Cost (ước tính)", formatCost(data.cost_estimate)],
  ];
  if (data.tool_calls != null) rows.splice(2, 0, ["Tool calls", data.tool_calls]);

  panel.innerHTML = `
    <p class="metric-section-title">${escapeHtml(title)}</p>
    ${rows.map(([k, v]) => `<div class="metric-row"><span>${k}</span><strong>${v}</strong></div>`).join("")}
  `;
}

function renderCompareMetrics(data) {
  const panel = $("metricsPanel");
  const cb = data.chatbot;
  const ag = data.agent;
  const cmp = data.comparison || {};
  panel.innerHTML = `
    <p class="metric-section-title">Chatbot</p>
    ${metricRowsHtml(cb)}
    <p class="metric-section-title">ReAct Agent</p>
    ${metricRowsHtml(ag)}
    <p class="metric-section-title">Chênh lệch</p>
    <div class="metric-row"><span>Δ tokens</span><strong>${cmp.token_delta ?? "—"}</strong></div>
    <div class="metric-row"><span>Δ cost</span><strong>${formatCost(cmp.cost_delta)}</strong></div>
  `;
}

function metricRowsHtml(d) {
  return [
    ["Total tokens", d.total_tokens],
    ["Cost", formatCost(d.cost_estimate)],
    ["LLM calls", d.llm_calls],
    ["Time", `${d.latency_ms} ms`],
  ]
    .map(([k, v]) => `<div class="metric-row"><span>${k}</span><strong>${v}</strong></div>`)
    .join("");
}

function showTrace(trace) {
  const section = $("traceSection");
  const pre = $("tracePanel");
  if (trace && trace.trim()) {
    section.hidden = false;
    pre.textContent = trace;
  } else {
    section.hidden = true;
    pre.textContent = "";
  }
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

async function loadConfig() {
  try {
    const data = await fetch("/api/config").then((r) => r.json());
    if (!data.ok) {
      $("config").innerHTML = `<span class="error">${escapeHtml(data.error)}</span>`;
      return;
    }
    $("config").innerHTML = `
      <div><strong>Provider:</strong> ${escapeHtml(data.provider)}</div>
      <div><strong>Model:</strong> ${escapeHtml(data.model)}</div>
      <div style="margin-top:0.35rem"><strong>Tools:</strong> ${data.tools.map(escapeHtml).join(", ")}</div>
    `;
  } catch {
    $("config").innerHTML = '<span class="error">Chạy: python app/server.py</span>';
  }
}

async function sendMessage() {
  const question = $("questionInput").value.trim();
  if (!question) return;

  const mode = getMode();
  const max_steps = parseInt($("maxSteps").value, 10) || 6;

  $("btnSend").disabled = true;
  appendMessage({ role: "user", body: question });
  $("questionInput").value = "";

  const loadingText =
    mode === "compare"
      ? "Đang hỏi Chatbot và ReAct Agent..."
      : mode === "chatbot"
        ? "Chatbot đang trả lời..."
        : "ReAct Agent đang suy luận...";
  appendMessage({ role: "loading", body: loadingText });

  try {
    if (mode === "chatbot") {
      const data = await postJson("/api/chatbot", { question });
      removeLoading();
      if (!data.ok) {
        appendMessage({ role: "error", body: data.error });
        return;
      }
      appendMessage({ role: "assistant", label: "Chatbot", body: data.answer, variant: "chatbot" });
      renderMetricsPanel(data, "Chatbot");
      showTrace(null);
    } else if (mode === "agent") {
      const data = await postJson("/api/agent", { question, max_steps });
      removeLoading();
      if (!data.ok) {
        appendMessage({ role: "error", body: data.error });
        return;
      }
      appendMessage({ role: "assistant", label: "ReAct Agent", body: data.answer, variant: "agent" });
      renderMetricsPanel(data, "ReAct Agent");
      showTrace(data.trace);
    } else {
      const data = await postJson("/api/compare", { question, max_steps });
      removeLoading();
      if (!data.ok) {
        appendMessage({ role: "error", body: data.error });
        return;
      }
      appendMessage({ role: "assistant", label: "Chatbot", body: data.chatbot.answer, variant: "chatbot" });
      appendMessage({ role: "assistant", label: "ReAct Agent", body: data.agent.answer, variant: "agent" });
      renderCompareMetrics(data);
      showTrace(data.agent.trace);
    }
  } catch (e) {
    removeLoading();
    appendMessage({ role: "error", body: String(e) });
  } finally {
    $("btnSend").disabled = false;
    $("questionInput").focus();
  }
}

$("btnSend").addEventListener("click", sendMessage);

$("questionInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

document.querySelectorAll(".hint-chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    $("questionInput").value = HINTS[parseInt(btn.dataset.hint, 10)];
    $("questionInput").focus();
  });
});

document.querySelectorAll('input[name="mode"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    if (getMode() !== "agent" && getMode() !== "compare") {
      showTrace(null);
    }
  });
});

loadConfig();
$("questionInput").focus();
