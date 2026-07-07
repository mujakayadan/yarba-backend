(function () {
  'use strict';

  var config = window.YARBA_CHAT;
  if (!config || !config.apiUrl) return;

  var root = document.getElementById('yarba-chat-root');
  if (!root) return;

  root.style.setProperty('--yarba-chat-primary', config.primaryColor || '#915EFF');
  root.style.setProperty('--yarba-chat-secondary', config.secondaryColor || '#1F2937');

  var state = {
    isOpen: false,
    isExpanded: false,
    isLoading: false,
    conversationId: sessionStorage.getItem('yarba_chat_conversation_id'),
    messages: [{ role: 'assistant', content: config.welcomeMessage }],
    history: [],
  };

  var els = {
    welcome: document.getElementById('yarba-chat-welcome'),
    welcomeText: document.getElementById('yarba-chat-welcome-text'),
    welcomeClose: document.getElementById('yarba-chat-welcome-close'),
    toggle: document.getElementById('yarba-chat-toggle'),
    panel: document.getElementById('yarba-chat-panel'),
    expand: document.getElementById('yarba-chat-expand'),
    close: document.getElementById('yarba-chat-close'),
    title: document.getElementById('yarba-chat-title'),
    messages: document.getElementById('yarba-chat-messages'),
    privacy: document.getElementById('yarba-chat-privacy'),
    form: document.getElementById('yarba-chat-form'),
    input: document.getElementById('yarba-chat-input'),
    send: document.getElementById('yarba-chat-send'),
  };

  els.title.textContent = 'Chat with ' + config.fullName;
  els.welcomeText.textContent =
    'Hey there! Would you like to talk to ' + config.fullName + "'s AI assistant? 👋";

  if (config.storeConversations && els.privacy) {
    els.privacy.textContent =
      'Chats may be stored for up to 90 days so ' +
      config.fullName +
      ' can review visitor questions. Do not share sensitive personal information.';
    els.privacy.classList.remove('yarba-hidden');
  }

  function escapeHtml(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function linkify(text) {
    return text.replace(/(https?:\/\/[^\s<]+)/g, function (url) {
      return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + url + '</a>';
    });
  }

  function renderMarkdownLite(text) {
    var html = escapeHtml(text);
    html = linkify(html);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  function renderMessages() {
    els.messages.innerHTML = '';
    state.messages.forEach(function (msg) {
      var row = document.createElement('div');
      row.className = 'yarba-chat-message ' + msg.role;
      var bubble = document.createElement('div');
      bubble.className = 'yarba-chat-bubble';
      bubble.innerHTML = renderMarkdownLite(msg.content);
      row.appendChild(bubble);
      els.messages.appendChild(row);
    });

    if (state.isLoading) {
      var loading = document.createElement('div');
      loading.className = 'yarba-chat-loading';
      loading.innerHTML = '<span></span><span></span><span></span>';
      els.messages.appendChild(loading);
    }

    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function setOpen(open) {
    state.isOpen = open;
    els.panel.classList.toggle('yarba-hidden', !open);
    els.toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      els.welcome.classList.add('yarba-hidden');
      renderMessages();
      els.input.focus();
    }
  }

  function setExpanded(expanded) {
    state.isExpanded = expanded;
    els.panel.classList.toggle('yarba-expanded', expanded);
    els.expand.innerHTML = expanded
      ? '<i class="fas fa-compress"></i>'
      : '<i class="fas fa-expand"></i>';
    els.expand.setAttribute('title', expanded ? 'Compress window' : 'Expand window');
    els.expand.setAttribute('aria-label', expanded ? 'Compress window' : 'Expand window');
  }

  function autoResizeTextarea() {
    els.input.style.height = 'auto';
    els.input.style.height = Math.min(els.input.scrollHeight, 150) + 'px';
  }

  function updateSendButton() {
    var hasText = els.input.value.trim().length > 0;
    els.send.disabled = !hasText || state.isLoading;
    if (state.isLoading) {
      els.send.innerHTML = '<span class="yarba-spinner"></span>';
    } else {
      els.send.textContent = 'Send';
    }
  }

  async function submitMessage(event) {
    event.preventDefault();
    var text = els.input.value.trim();
    if (!text || state.isLoading) return;

    state.messages.push({ role: 'user', content: text });
    state.history.push({ role: 'user', content: text });
    els.input.value = '';
    autoResizeTextarea();
    state.isLoading = true;
    updateSendButton();
    renderMessages();

    try {
      var payload = {
        subdomain: config.subdomain,
        message: text,
        conversation_id: state.conversationId,
        history:
          config.storeConversations && state.conversationId
            ? []
            : state.history.slice(0, -1),
      };

      var response = await fetch(config.apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      var data = await response.json();
      state.conversationId = data.conversation_id;
      sessionStorage.setItem('yarba_chat_conversation_id', data.conversation_id);

      var reply = data.response || '';
      state.messages.push({ role: 'assistant', content: reply });
      state.history.push({ role: 'assistant', content: reply });
    } catch (err) {
      console.error('YARBA chat error:', err);
      state.messages.push({
        role: 'assistant',
        content: 'Sorry, I had trouble responding. Please try again in a moment.',
      });
    } finally {
      state.isLoading = false;
      updateSendButton();
      renderMessages();
    }
  }

  els.toggle.addEventListener('click', function () {
    setOpen(!state.isOpen);
  });

  els.close.addEventListener('click', function () {
    setOpen(false);
  });

  els.expand.addEventListener('click', function () {
    setExpanded(!state.isExpanded);
  });

  els.welcomeClose.addEventListener('click', function () {
    els.welcome.classList.add('yarba-hidden');
  });

  els.input.addEventListener('input', function () {
    autoResizeTextarea();
    updateSendButton();
  });

  els.input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitMessage(event);
    }
  });

  els.form.addEventListener('submit', submitMessage);

  if (!sessionStorage.getItem('yarba_chat_welcome_shown')) {
    setTimeout(function () {
      if (!state.isOpen) {
        els.welcome.classList.remove('yarba-hidden');
        sessionStorage.setItem('yarba_chat_welcome_shown', '1');
      }
    }, 10000);
  }

  updateSendButton();
})();
