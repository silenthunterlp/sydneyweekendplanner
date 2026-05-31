(function () {
  const messages = document.getElementById("messages");
  const input = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");

  // Persist session ID across page refreshes so conversation memory is retained
  let sessionId = sessionStorage.getItem("sydney_session_id");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem("sydney_session_id", sessionId);
  }

  const wsUrl = `ws://${location.host}/ws/${sessionId}`;
  let ws;

  function connect() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      appendMessage("assistant", "G'day! I'm your Sydney Weekend Planner. Ask me to plan your weekend, or tell me what you're in the mood for!");
    };

    ws.onmessage = (event) => {
      removeThinking();
      appendMessage("assistant", event.data);
      setInputEnabled(true);
    };

    ws.onclose = () => {
      setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function showThinking() {
    const div = document.createElement("div");
    div.className = "message thinking";
    div.id = "thinking-indicator";
    div.textContent = "Planning your weekend…";
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeThinking() {
    const el = document.getElementById("thinking-indicator");
    if (el) el.remove();
  }

  function setInputEnabled(enabled) {
    input.disabled = !enabled;
    sendBtn.disabled = !enabled;
    if (enabled) input.focus();
  }

  function send() {
    const text = input.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    appendMessage("user", text);
    input.value = "";
    setInputEnabled(false);
    showThinking();
    ws.send(text);
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  connect();
})();
