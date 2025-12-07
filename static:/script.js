const input = document.getElementById('message');
const chat = document.getElementById('chat');
const sendBtn = document.getElementById('sendBtn');

// 🔹 Formatowane dodawanie wiadomości
function addMessage(text, sender) {
  const msg = document.createElement('div');
  msg.classList.add('message', sender);

  if (sender === 'bot') {
    let formatted = text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")  // pogrubienie markdown
      .replace(/\n{2,}/g, "<br><br>")                    // duży odstęp (2+ nowe linie)
      .replace(/\n/g, "<br>");                           // zwykły enter = nowa linia

    msg.innerHTML = `
      <div class="avatar">P</div>
      <div class="message-content">${formatted}</div>
    `;
  } else {
    msg.innerHTML = `<div class="message-content">${text}</div>`;
  }

  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

// Animacja "pisania"
function showTyping() {
  const typing = document.createElement('div');
  typing.classList.add('message', 'bot');
  typing.id = 'typing';
  typing.innerHTML = `
    <div class="avatar">P</div>
    <div class="message-content"><span class="dot">•</span><span class="dot">•</span><span class="dot">•</span></div>
  `;
  chat.appendChild(typing);
  chat.scrollTop = chat.scrollHeight;
}
function hideTyping() {
  const t = document.getElementById('typing');
  if (t) t.remove();
}

// Wiadomość powitalna
async function loadWelcome() {
  showTyping();
  try {
    const res = await fetch('/start');
    const data = await res.json();
    hideTyping();
    addMessage(data.reply, 'bot');
  } catch {
    hideTyping();
    addMessage("Cześć! 👋 Jestem Beauty Ekspertką — zapytaj mnie o makijaż permanentny 💋✨", "bot");
  }
}
loadWelcome();

// Wysyłanie wiadomości
async function sendMessage() {
  const msg = input.value.trim();
  if (!msg) return;

  addMessage(msg, 'user');
  input.value = '';
  showTyping();

  const response = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg })
  });
  const data = await response.json();

  await new Promise(r => setTimeout(r, 1200));

  hideTyping();
  addMessage(data.reply, 'bot');
}

// Obsługa Enter i kliknięcia
input.addEventListener('keydown', e => {
  if (e.key === 'Enter') sendMessage();
});
sendBtn.addEventListener('click', sendMessage);