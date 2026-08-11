const chatLog = document.getElementById("chat-log");
const emptyState = document.getElementById("empty-state");
const composer = document.getElementById("composer");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const attachBtn = document.getElementById("attach-btn");
const fileInput = document.getElementById("file-input");
const dropOverlay = document.getElementById("drop-overlay");
const newChatBtn = document.getElementById("new-chat");

const TOOL_LABELS = {
  tech_llm_tool: "Tech LLM Tool",
  code_llm_tool: "Code LLM Tool",
  general_llm_tool: "General LLM Tool",
};

let supportedFormats = [];
let isSending = false;

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

  let toolStatusEl = null;
  let answerEl = null;

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

        if (event.type === "tool_start") {
          toolStatusEl = addToolStatus(event.tool);
        } else if (event.type === "tool_end") {
          if (toolStatusEl) {
            toolStatusEl.remove();
            toolStatusEl = null;
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
    if (toolStatusEl) toolStatusEl.remove();
    addErrorMessage(`답변을 받지 못했습니다: ${err.message}`, () => sendMessage(text));
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();
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
