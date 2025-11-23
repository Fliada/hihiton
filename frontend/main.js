const API_BASE_URL = (window.APP_CONFIG?.apiBaseUrl ?? window.location.origin).replace(
  /\/$/,
  "",
);

const elements = {
  messages: document.getElementById("messages"),
  form: document.getElementById("chat-form"),
  textarea: document.getElementById("message-input"),
  sendButton: document.getElementById("send-button"),
  status: document.getElementById("status-badge"),
};

const STORAGE_KEYS = {
  session: "hihiton-web-session",
  messages: "hihiton-web-messages",
};

const storage = (() => {
  try {
    const key = "__storage_probe__";
    sessionStorage.setItem(key, "1");
    sessionStorage.removeItem(key);
    return sessionStorage;
  } catch {
    return null;
  }
})();

const createId = () =>
  window.crypto?.randomUUID
    ? window.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const sessionId =
  (storage && storage.getItem(STORAGE_KEYS.session)) || createId();

if (storage && !storage.getItem(STORAGE_KEYS.session)) {
  storage.setItem(STORAGE_KEYS.session, sessionId);
}

let messages = [];

if (storage) {
  try {
    const cached = storage.getItem(STORAGE_KEYS.messages);
    if (cached) {
      messages = JSON.parse(cached);
    }
  } catch {
    messages = [];
  }
}

renderMessages();

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = elements.textarea.value.trim();
  if (!text) {
    return;
  }
  elements.textarea.value = "";
  handleUserMessage(text);
});

function handleUserMessage(text) {
  appendMessage({
    id: createId(),
    sender: "user",
    text,
    timestamp: Date.now(),
  });
  sendToAgent(text);
}

function setSendingState(isSending) {
  elements.sendButton.disabled = isSending;
  elements.textarea.disabled = isSending;
}

function updateStatus(text, mode = "idle") {
  elements.status.textContent = text;
  elements.status.classList.remove("status-badge--busy", "status-badge--error");
  if (mode === "busy") {
    elements.status.classList.add("status-badge--busy");
  } else if (mode === "error") {
    elements.status.classList.add("status-badge--error");
  }
}

async function sendToAgent(message) {
  setSendingState(true);
  updateStatus("Обрабатываем запрос...", "busy");

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      let detail = "Неизвестная ошибка";
      try {
        const errorPayload = await response.json();
        detail = errorPayload?.detail ?? detail;
      } catch {
        detail = response.statusText;
      }
      throw new Error(detail);
    }

    const data = await response.json();
    const csvPayload = data.csv
      ? {
          headers: data.csv.headers ?? [],
          rows: data.csv.rows ?? [],
          downloadUrl: toAbsoluteUrl(data.csv.download_url ?? data.csv.downloadUrl),
        }
      : null;

    const pngPayload = data.png
      ? {
          downloadUrl: toAbsoluteUrl(data.png.download_url ?? data.png.downloadUrl),
          dataUrl: `data:image/png;base64,${data.png.image_base64}`,
        }
      : null;

    appendMessage({
      id: createId(),
      sender: "bot",
      text: data.text ?? "",
      csv: csvPayload,
      png: pngPayload,
      timestamp: Date.now(),
    });

    updateStatus("Готов к работе");
  } catch (error) {
    updateStatus("Ошибка запроса", "error");
    appendMessage({
      id: createId(),
      sender: "bot",
      text: `Не удалось обработать запрос: ${error.message}`,
      timestamp: Date.now(),
      isError: true,
    });
  } finally {
    setSendingState(false);
    elements.textarea.focus();
  }
}

function appendMessage(message) {
  messages.push(message);
  if (storage) {
    storage.setItem(STORAGE_KEYS.messages, JSON.stringify(messages));
  }
  renderMessages();
}

function renderMessages() {
  elements.messages.innerHTML = "";
  if (!messages.length) {
    const placeholder = document.createElement("div");
    placeholder.className = "message message--bot";
    placeholder.innerHTML =
      "<div class='message__meta'>бот</div><p class='message__text'>Здравствуйте! Задайте вопрос, чтобы получить данные. CSV и графики будут показаны прямо здесь.</p>";
    elements.messages.appendChild(placeholder);
    return;
  }

  for (const message of messages) {
    elements.messages.appendChild(renderMessageNode(message));
  }

  elements.messages.scrollTo({
    top: elements.messages.scrollHeight,
    behavior: "smooth",
  });
}

function renderMessageNode(message) {
  const article = document.createElement("article");
  article.className = `message message--${message.sender}`;
  if (message.isError) {
    article.classList.add("message--error");
  }

  const meta = document.createElement("div");
  meta.className = "message__meta";
  meta.textContent = `${message.sender === "user" ? "Вы" : "Бот"} • ${formatTime(
    message.timestamp,
  )}`;
  article.appendChild(meta);

  const text = document.createElement("p");
  text.className = "message__text";
  text.textContent = message.text || "";
  article.appendChild(text);

  if (message.csv) {
    article.appendChild(renderCsvPreview(message.csv));
  }

  if (message.png) {
    article.appendChild(renderImagePreview(message.png));
  }

  return article;
}

function renderCsvPreview(csvPayload) {
  const container = document.createElement("div");
  container.className = "csv-preview";

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");

  csvPayload.headers.forEach((header) => {
    const th = document.createElement("th");
    th.textContent = header;
    headerRow.appendChild(th);
  });

  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  csvPayload.rows.forEach((row) => {
    const tr = document.createElement("tr");
    row.forEach((cell) => {
      const td = document.createElement("td");
      td.textContent = cell;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  container.appendChild(table);

  const link = document.createElement("a");
  link.href = csvPayload.downloadUrl;
  link.className = "download-link";
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "Скачать CSV";
  container.appendChild(link);

  return container;
}

function renderImagePreview(pngPayload) {
  const wrapper = document.createElement("div");
  wrapper.className = "image-preview";

  const img = document.createElement("img");
  img.src = pngPayload.dataUrl;
  img.alt = "Результирующее изображение";
  wrapper.appendChild(img);

  const link = document.createElement("a");
  link.href = pngPayload.downloadUrl;
  link.className = "download-link";
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "Скачать изображение";
  wrapper.appendChild(link);

  return wrapper;
}

function toAbsoluteUrl(path = "") {
  try {
    return new URL(path, `${API_BASE_URL}/`).toString();
  } catch {
    return path;
  }
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}
