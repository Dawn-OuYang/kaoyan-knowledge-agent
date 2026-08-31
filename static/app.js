const state = {
  mode: "qa",
  specialty: "全部",
};

const specialtyEl = document.querySelector("#specialty");
const form = document.querySelector("#askForm");
const questionEl = document.querySelector("#question");
const conversation = document.querySelector("#conversation");
const demoBtn = document.querySelector("#demoBtn");
const planFields = document.querySelector(".plan-fields");

const demos = {
  qa: "顺序表和链表的区别是什么？",
  exam: "真题解析：为什么 TCP 建立连接需要三次握手？",
  school: "报考计算机专业时，招生简章和参考书应该怎么核验？",
  plan: "距离考试 120 天，计算机专业课应该怎么安排？",
};

async function init() {
  const [specialtyRes, statusRes] = await Promise.all([fetch("/api/specialties"), fetch("/api/status")]);
  const specialtyData = await specialtyRes.json();
  const statusData = await statusRes.json();
  specialtyEl.innerHTML = specialtyData.specialties
    .map((item) => `<option value="${item}">${item}</option>`)
    .join("");
  document.querySelector("#knowledgeCount").textContent = String(statusData.knowledge_items);
  document.querySelector("#modelStatus").textContent = statusData.model_gateway.enabled
    ? statusData.model_gateway.model
    : "本地模板";
  updateMode();
}

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-mode]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.mode = button.dataset.mode;
    updateMode();
  });
});

specialtyEl.addEventListener("change", () => {
  state.specialty = specialtyEl.value;
});

demoBtn.addEventListener("click", () => {
  questionEl.value = demos[state.mode] || demos.qa;
  questionEl.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionEl.value.trim();
  if (!question) return;

  clearEmpty();
  addMessage("user", question);
  questionEl.value = "";
  const loading = addMessage("agent", "正在检索知识库并组织回答...");

  const payload = {
    question,
    specialty: specialtyEl.value,
    mode: state.mode,
    profile: {
      target: document.querySelector("#target").value,
      days: document.querySelector("#days").value,
      level: document.querySelector("#level").value,
    },
  };

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    loading.remove();
    addAnswer(data);
  } catch (error) {
    loading.remove();
    addMessage("agent error", "请求失败，请确认本地服务仍在运行。");
  }
});

function updateMode() {
  planFields.style.display = state.mode === "plan" ? "grid" : "none";
}

function clearEmpty() {
  const empty = conversation.querySelector(".empty-state");
  if (empty) empty.remove();
}

function addMessage(role, text) {
  const node = document.createElement("article");
  node.className = `message ${role}`;
  node.innerHTML = `<div class="bubble">${escapeHtml(text).replace(/\n/g, "<br>")}</div>`;
  conversation.appendChild(node);
  conversation.scrollTop = conversation.scrollHeight;
  return node;
}

function addAnswer(data) {
  const node = document.createElement("article");
  node.className = "message agent";
  const citations = (data.citations || [])
    .map(
      (item) => `
        <li>
          <strong>${citationTitle(item)}</strong>
          <span>${citationMeta(item)}</span>
        </li>`,
    )
    .join("");
  const warnings = (data.warnings || []).map((item) => `<p class="warning">${escapeHtml(item)}</p>`).join("");
  node.innerHTML = `
    <div class="answer-card">
      <div class="answer-meta">
        <span>${escapeHtml(data.route)}</span>
        <span>置信度：${escapeHtml(data.confidence)}</span>
        <span>${escapeHtml(data.model_provider || "local-template")}</span>
        <span>总耗时：${escapeHtml(data.timings?.total_ms ?? "-")} ms</span>
      </div>
      <div class="answer-text">${escapeHtml(data.answer).replace(/\n/g, "<br>")}</div>
      ${warnings}
      <details open>
        <summary>引用来源</summary>
        <ul class="citations">${citations || "<li>暂无引用</li>"}</ul>
      </details>
    </div>`;
  conversation.appendChild(node);
  conversation.scrollTop = conversation.scrollHeight;
}

function citationTitle(item) {
  const title = escapeHtml(item.title);
  if (!item.source_url) return title;
  const url = escapeHtml(item.source_url);
  return `<a href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>`;
}

function citationMeta(item) {
  const parts = [item.source, item.subject];
  if (item.year) parts.push(`年份 ${item.year}`);
  if (item.retrieved_at) parts.push(`采集 ${item.retrieved_at}`);
  if (item.risk_level === "time_sensitive") parts.push("时效敏感");
  return parts.filter(Boolean).map(escapeHtml).join(" / ");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

init();
