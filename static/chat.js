(function () {
  const messages = document.getElementById("messages");
  const input = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");

  // Persist session ID so conversation memory is retained across page refreshes
  let sessionId = sessionStorage.getItem("sydney_session_id");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem("sydney_session_id", sessionId);
  }

  // Use wss:// on HTTPS (Render/production), ws:// on HTTP (local dev)
  const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${location.host}/ws/${sessionId}`;
  let ws;
  let reconnectTimer;

  function setStatus(state) {
    // state: "connecting" | "connected" | "disconnected"
    const dot = statusDot;
    const text = statusText;
    dot.className = "status-dot " + state;
    if (state === "connected") text.textContent = "Connected";
    else if (state === "connecting") text.textContent = "Connecting…";
    else text.textContent = "Reconnecting…";
  }

  function connect() {
    clearTimeout(reconnectTimer);
    setStatus("connecting");
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setStatus("connected");
      appendMessage("assistant", "G'day! 🌊 I'm your Sydney Weekend Planner.\n\nAsk me to plan your weekend, or say what you're in the mood for!");
      setInputEnabled(true);
    };

    ws.onmessage = (event) => {
      removeThinking();
      appendMessage("assistant", event.data);
      setInputEnabled(true);
    };

    ws.onclose = () => {
      setStatus("disconnected");
      setInputEnabled(false);
      reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }

  // Convert basic markdown to HTML for richer display
  function renderMarkdown(text) {
    return text
      // Tables: render as HTML table
      .replace(/^\|(.+)\|$/gm, (line) => {
        const cells = line.slice(1, -1).split("|").map(c => c.trim());
        const isHeader = false;
        return `<tr>${cells.map(c => `<td>${c}</td>`).join("")}</tr>`;
      })
      .replace(/(<tr>.*<\/tr>\n?)+/gs, (block) => {
        const rows = block.trim().split("\n").filter(r => r.includes("<tr>") && !r.match(/^<tr><td>[-: |]+<\/td>/));
        if (rows.length > 1) {
          return `<table>${rows[0].replace(/<td>/g,"<th>").replace(/<\/td>/g,"</th>")}${rows.slice(1).join("")}</table>`;
        }
        return `<table>${rows.join("")}</table>`;
      })
      // Bold
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      // Headers
      .replace(/^### (.+)$/gm, "<h3>$1</h3>")
      .replace(/^## (.+)$/gm, "<h2>$1</h2>")
      // Horizontal rule
      .replace(/^---$/gm, "<hr>")
      // Line breaks
      .replace(/\n/g, "<br>");
  }

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    if (role === "assistant") {
      div.innerHTML = renderMarkdown(text);
    } else {
      div.textContent = text;
    }
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function showThinking() {
    const div = document.createElement("div");
    div.className = "message thinking";
    div.id = "thinking-indicator";
    div.innerHTML = '<span class="dot-pulse">●</span><span class="dot-pulse">●</span><span class="dot-pulse">●</span> Planning your weekend…';
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
    // Hide suggestion chips after first message is sent
    if (chipBar) chipBar.style.display = "none";
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  // Quick-start suggestion chips
  const suggestions = [
    "Plan my weekend 🗓️",
    "Free things to do 💚",
    "Best beaches this weekend 🏖️",
    "Food & markets 🥗",
    "Live music Saturday night 🎵",
  ];

  const chipBar = document.getElementById("suggestion-chips");
  if (chipBar) {
    suggestions.forEach(s => {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.textContent = s;
      btn.addEventListener("click", () => {
        if (ws && ws.readyState === WebSocket.OPEN && !input.disabled) {
          input.value = s;
          send();
          chipBar.style.display = "none";
        }
      });
      chipBar.appendChild(btn);
    });
  }

  // Hide chips after first user message
  const origSend = send;

  connect();
})();
