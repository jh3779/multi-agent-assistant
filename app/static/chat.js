const chatLog = document.getElementById("chat-log");
const emptyState = document.getElementById("empty-state");
const composer = document.getElementById("composer");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const attachBtn = document.getElementById("attach-btn");
const fileInput = document.getElementById("file-input");
const dropOverlay = document.getElementById("drop-overlay");
const newChatBtn = document.getElementById("new-chat");
const agentSelector = document.getElementById("agent-selector");
const logPanel = document.getElementById("log-panel");
const logPanelBody = document.getElementById("log-panel-body");
const logPanelClose = document.getElementById("log-panel-close");
const logProgress = document.getElementById("log-progress");

const TOOL_LABELS = {
  tech_llm_tool: "Tech LLM Tool",
  code_llm_tool: "Code LLM Tool",
  general_llm_tool: "General LLM Tool",
  file_converter: "파일 변환",
  web_search: "웹 검색",
  date_time: " 현재 시간 조회",
};

let supportedFormats = [];
let isSending = false;
let selectedAgent = "file_converter";

agentSelector.querySelectorAll(".agent-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.disabled) return;
    selectedAgent = btn.dataset.agent;
    agentSelector
      .querySelectorAll(".agent-btn")
      .forEach((b) => b.classList.toggle("active", b === btn));
  });
});

function hideEmptyState() {
  emptyState.style.display = "none";
}

function scrollToBottom() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addMessage(role, text) {
  hideEmptyState();
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.textContent = text;
  chatLog.appendChild(el);
  scrollToBottom();
  return el;
}

function addToolStatus(toolName) {
  hideEmptyState();
  const el = document.createElement("div");
  el.className = "tool-status";
  el.innerHTML = `<span class="dot" aria-hidden="true"></span><span>${
    TOOL_LABELS[toolName] || toolName
  } 호출 중...</span>`;
  chatLog.appendChild(el);
  scrollToBottom();
  return el;
}

function addProcessingIndicator() {
  hideEmptyState();
  const el = document.createElement("div");
  el.className = "tool-status";
  el.innerHTML = `<span class="dot" aria-hidden="true"></span><span>처리 중...</span>`;
  chatLog.appendChild(el);
  scrollToBottom();
  return el;
}

function addErrorMessage(text, onRetry) {
  hideEmptyState();
  const el = document.createElement("div");
  el.className = "message error";
  el.textContent = text;
  if (!onRetry) {
    chatLog.appendChild(el);
    scrollToBottom();
    return;
  }
  const retry = document.createElement("button");
  retry.type = "button";
  retry.className = "retry-btn";
  retry.textContent = "다시 시도";
  retry.addEventListener("click", () => {
    el.remove();
    onRetry();
  });
  el.appendChild(document.createElement("br"));
  el.appendChild(retry);
  chatLog.appendChild(el);
  scrollToBottom();
}

async function sendMessage(text) {
  if (isSending) return;
  isSending = true;
  addMessage("user", text);
  sendBtn.disabled = true;
  messageInput.disabled = true;

  try {
    if (selectedAgent === "kbo") {
      await sendToKBO(text);
    } else {
      await sendToFileConverter(text);
    }
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();
  }
}

async function sendToKBO(text) {
  const processingEl = addProcessingIndicator();

  try {
    const res = await fetch("/kbo/invoke", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text }),
    });

    if (!res.ok) {
      throw new Error(`서버 오류 (${res.status})`);
    }

    const data = await res.json();
    processingEl.remove();
    addMessage("assistant", data.answer);
  } catch (err) {
    processingEl.remove();
    addErrorMessage(`답변을 받지 못했습니다: ${err.message}`, () => sendMessage(text));
  }
}

async function sendToFileConverter(text) {
  const toolStatusEls = new Map();
  let answerEl = null;
  let processingEl = addProcessingIndicator();

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!res.ok || !res.body) {
      throw new Error(`서버 오류 (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop();

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const event = JSON.parse(line.slice(5).trim());

        if (processingEl && event.type !== "done") {
          processingEl.remove();
          processingEl = null;
        }

        if (event.type === "tool_start") {
          const el = addToolStatus(event.tool);
          toolStatusEls.set(event.tool, el);

          } else if (event.type === "tool_end") {
            const el = toolStatusEls.get(event.tool);

            if (el) {
              el.remove();
              toolStatusEls.delete(event.tool);
            }
          } else if (event.type === "answer_chunk") {
          if (!answerEl) {
            answerEl = addMessage("assistant", "");
            answerEl.classList.add("streaming");
          }
          answerEl.textContent += event.content;
          scrollToBottom();
        } else if (event.type === "done") {
          if (answerEl) answerEl.classList.remove("streaming");
        }
      }
    }
  } catch (err) {
    for (const el of toolStatusEls.values()) {
      el.remove();
    }

    toolStatusEls.clear();
    addErrorMessage(`답변을 받지 못했습니다: ${err.message}`, () => sendMessage(text));
  } finally {
    if (processingEl) processingEl.remove();
  }
}

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = "";
  messageInput.style.height = "auto";
  sendMessage(text);
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = `${messageInput.scrollHeight}px`;
});

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    composer.requestSubmit();
  }
});

newChatBtn.addEventListener("click", () => {
  chatLog.querySelectorAll(".message, .tool-status, .file-picker").forEach((el) => el.remove());
  emptyState.style.display = "";
});

// --- 파일 업로드 (file-converter) ---

let formatsReady = null;

async function loadSupportedFormats() {
  try {
    const res = await fetch("/tools/file-converter/formats");
    const data = await res.json();
    supportedFormats = data.supported_formats || [];
  } catch {
    supportedFormats = [];
  }
}
formatsReady = loadSupportedFormats();

function getExtension(filename) {
  const i = filename.lastIndexOf(".");
  return i === -1 ? "" : filename.slice(i + 1).toLowerCase();
}

const PAPERCLIP_ICON =
  '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M17.5 8.5 9.6 16.4a3 3 0 1 1-4.24-4.25l8.49-8.48a2 2 0 1 1 2.83 2.83l-8.13 8.13a1 1 0 1 1-1.42-1.42l7.07-7.07" stroke-linecap="round" stroke-linejoin="round"/></svg>';

function addFilePicker(file) {
  hideEmptyState();
  const el = document.createElement("div");
  el.className = "message user file-picker";

  const label = document.createElement("div");
  label.className = "file-picker-label";
  label.innerHTML = `${PAPERCLIP_ICON}<span></span>`;
  label.querySelector("span").textContent = `${file.name} — 변환할 포맷을 선택하세요`;
  el.appendChild(label);

  const row = document.createElement("div");
  row.style.marginTop = "8px";
  row.style.display = "flex";
  row.style.gap = "8px";

  const sourceExt = getExtension(file.name);
  const select = document.createElement("select");
  select.style.flex = "1";
  for (const fmt of supportedFormats) {
    if (fmt === sourceExt) continue; // 원본과 같은 포맷으로 변환하는 옵션은 제외
    const opt = document.createElement("option");
    opt.value = fmt;
    opt.textContent = fmt;
    select.appendChild(opt);
  }
  row.appendChild(select);

  const convertBtn = document.createElement("button");
  convertBtn.type = "button";
  convertBtn.className = "btn-ghost";
  convertBtn.textContent = "변환";
  convertBtn.addEventListener("click", () => {
    el.remove();
    convertFile(file, select.value);
  });
  row.appendChild(convertBtn);

  el.appendChild(row);
  chatLog.appendChild(el);
  scrollToBottom();
}

async function convertFile(file, targetFormat) {
  hideEmptyState();
  const statusEl = addToolStatus("file-converter");
  statusEl.querySelector("span:last-child").textContent = "file-converter 변환 중...";

  const form = new FormData();
  form.append("file", file);
  form.append("target_format", targetFormat);

  try {
    const res = await fetch("/tools/file-converter/convert", { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `변환 실패 (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    statusEl.remove();
    const resultEl = document.createElement("div");
    resultEl.className = "file-result";
    resultEl.innerHTML = `<span>변환 완료:</span> <a href="${url}" download="converted.${targetFormat}">converted.${targetFormat} 다운로드</a>`;
    chatLog.appendChild(resultEl);
    scrollToBottom();
  } catch (err) {
    statusEl.remove();
    addErrorMessage(`파일 변환 실패: ${err.message}`, () => convertFile(file, targetFormat));
  }
}

async function handleIncomingFile(file) {
  if (!file) return;

  // 페이지 로드 직후 드롭하면 /formats 응답이 아직 안 왔을 수 있음 — 그 요청이
  // 끝날 때까지 기다린 뒤 검사한다(안 그러면 지원 목록이 비어있어 뭘 올려도
  // "지원하지 않는 파일 형식"으로 잘못 뜸).
  if (formatsReady) await formatsReady;

  // 파일이 드롭된 즉시(변환 포맷을 고르기 전에) 원본 확장자가 지원되는지 먼저 확인 —
  // 안 그러면 사용자가 포맷을 고르고 "변환"을 눌러야만 실패를 알 수 있었음.
  const ext = getExtension(file.name);
  if (!ext) {
    addErrorMessage(`"${file.name}"에 확장자가 없어 원본 포맷을 알 수 없습니다.`);
    return;
  }
  if (!supportedFormats.includes(ext)) {
    addErrorMessage(
      `"${file.name}"(.${ext})은 지원하지 않는 파일 형식입니다. 지원 포맷: ${supportedFormats.join(", ")}`
    );
    return;
  }

  addFilePicker(file);
}

attachBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  handleIncomingFile(fileInput.files[0]);
  fileInput.value = "";
});

let dragCounter = 0;
window.addEventListener("dragenter", (e) => {
  e.preventDefault();
  dragCounter += 1;
  dropOverlay.hidden = false;
});
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("dragleave", () => {
  dragCounter -= 1;
  if (dragCounter <= 0) {
    dragCounter = 0;
    dropOverlay.hidden = true;
  }
});
window.addEventListener("drop", (e) => {
  e.preventDefault();
  dragCounter = 0;
  dropOverlay.hidden = true;
  const file = e.dataTransfer.files[0];
  handleIncomingFile(file);
});

// --- 히든 로그 사이드바 ('\' 키로 토글) ---
//
// 백엔드 로그 텍스트 자체는 그대로 보여주되(log-panel-body), 그 위에 에이전트별
// "지금 어느 단계인지"를 요약하는 진행 카드(log-progress)를 얹는다. 카드 상태는
// 이미 존재하는 로그 메시지의 "[TAG] ..." 접두사를 해석해서만 만든다 — 에이전트
// 코드(kbo_agent.py/file_converter_agent.py) 자체는 건드리지 않는다.

// agent-selector 버튼(4개)과 1:1로 대응 — 새 에이전트가 백엔드에 연결되면 logger만
// 채워주면 된다(business/agent4는 아직 로거가 없어 "미연결" 상태로 남는다).
const AGENT_META = [
  { key: "file_converter", label: "파일 변환", logger: "app.llms.file_converter_agent" },
  { key: "kbo", label: "KBO", logger: "app.llms.kbo_agent" },
  { key: "business", label: "비즈니스", logger: null },
  { key: "agent4", label: "준비 중", logger: null },
];

const LOGGER_TO_AGENT = Object.fromEntries(
  AGENT_META.filter((a) => a.logger).map((a) => [a.logger, a.key])
);

const agentProgress = {};
AGENT_META.forEach((a) => {
  agentProgress[a.key] = { stage: a.logger ? "대기 중" : "미연결", time: null };
});

// 도구(app.tools.*) 로그는 메시지 자체에 어느 에이전트가 호출했는지 정보가 없다
// — 현재 구조상 요청이 한 번에 하나씩 순차 처리되므로, 가장 최근에 [MODEL] 단계를
// 시작한 에이전트가 호출한 도구라고 보는 게 합리적인 근사치다.
let lastActiveAgentKey = null;
let logEventSource = null;
let logEventSourceOpen = false;

function deriveStage(message) {
  if (message.startsWith("[MODEL]")) return "모델 호출 중";
  if (message.startsWith("[TOOL]")) {
    const detail = message.replace(/^\[TOOL\]\s*/, "");
    return detail.includes("실패") || /failed/i.test(detail)
      ? `도구 실행 실패 — ${detail}`
      : `도구 실행 중 — ${detail}`;
  }
  if (message.startsWith("[DRAFT]")) return "초안 생성 완료";
  if (message.startsWith("[EVIDENCE]")) return "근거 수집 중";
  if (message.startsWith("[VALIDATION] Validating")) return "답변 검증 중";
  if (message.startsWith("[VALIDATION] Passed")) return "검증 통과 — 완료";
  if (message.startsWith("[VALIDATION] Failed")) return "검증 실패 — 보정 필요";
  if (message.startsWith("[CORRECTION] Correcting")) return "답변 보정 중";
  if (message.startsWith("[CORRECTION] Corrected")) return "보정 완료";
  if (message.startsWith("[TIME]")) return "완료";
  return null;
}

function renderProgress() {
  logProgress.innerHTML = "";
  for (const meta of AGENT_META) {
    const state = agentProgress[meta.key];
    const card = document.createElement("div");
    card.className = "log-progress-card";
    if (!meta.logger) {
      card.classList.add("disabled");
    } else if (meta.key === lastActiveAgentKey && state.stage !== "대기 중") {
      card.classList.add("active");
    } else {
      card.classList.add("idle");
    }

    const head = document.createElement("div");
    head.className = "log-progress-card-head";
    const nameEl = document.createElement("span");
    nameEl.textContent = meta.label;
    head.appendChild(nameEl);
    if (state.time) {
      const timeEl = document.createElement("span");
      timeEl.className = "log-progress-card-time";
      timeEl.textContent = state.time;
      head.appendChild(timeEl);
    }
    card.appendChild(head);

    const stageEl = document.createElement("div");
    stageEl.className = "log-progress-card-stage";
    stageEl.textContent = state.stage;
    card.appendChild(stageEl);

    logProgress.appendChild(card);
  }
}

function appendLogEntry(entry) {
  const line = document.createElement("div");
  line.className = `log-line log-${(entry.level || "").toLowerCase()}`;
  line.textContent = `[${entry.time}] ${entry.level} ${entry.logger} — ${entry.message}`;
  logPanelBody.appendChild(line);
  logPanelBody.scrollTop = logPanelBody.scrollHeight;

  const agentKey = LOGGER_TO_AGENT[entry.logger];
  if (agentKey) {
    lastActiveAgentKey = agentKey;
  }
  const targetKey = agentKey || lastActiveAgentKey;
  if (!targetKey) return;

  const stage = deriveStage(entry.message);
  if (stage) {
    agentProgress[targetKey] = { stage, time: entry.time };
    renderProgress();
  }
}

function resetProgress() {
  AGENT_META.forEach((a) => {
    agentProgress[a.key] = { stage: a.logger ? "대기 중" : "미연결", time: null };
  });
  lastActiveAgentKey = null;
  renderProgress();
}

function openLogPanel() {
  logPanel.hidden = false;
  if (logEventSourceOpen) return;
  logEventSourceOpen = true;
  logPanelBody.innerHTML = "";
  resetProgress();
  logEventSource = new EventSource("/logs/stream");
  logEventSource.onmessage = (e) => {
    appendLogEntry(JSON.parse(e.data));
  };
}

function closeLogPanel() {
  logPanel.hidden = true;
  if (logEventSource) {
    logEventSource.close();
    logEventSource = null;
  }
  logEventSourceOpen = false;
}

renderProgress();
logPanelClose.addEventListener("click", closeLogPanel);

window.addEventListener("keydown", (e) => {
  if (e.key !== "\\") return;
  // 메시지 입력창에 타이핑 중이면 평범한 백슬래시 문자로 취급 — 히든 키는
  // 입력창 밖에서 눌렀을 때만 동작한다.
  const activeTag = document.activeElement && document.activeElement.tagName;
  if (activeTag === "TEXTAREA" || activeTag === "INPUT") return;
  e.preventDefault();
  if (logPanel.hidden) {
    openLogPanel();
  } else {
    closeLogPanel();
  }
});
