/**
 * DevTrack AI - Embeddable Chat Widget
 * 
 * Usage:
 * <script src="https://yourserver.com/widget/widget.js" data-business="your-business-slug"></script>
 * 
 * This creates a floating chat bubble that opens a chat window
 * connected to the DevTrack AI system.
 */
(function() {
    'use strict';

    // Get configuration from script tag
    const script = document.currentScript;
    const businessSlug = script?.getAttribute('data-business') || 'demo';
    const apiBase = script?.src ? new URL(script.src).origin + '/api/v1' : 'http://localhost:8000/api/v1';

    // State
    let isOpen = false;
    let customerId = localStorage.getItem('devtrack_widget_customer') || null;
    let conversationId = null;
    let businessInfo = null;

    // ─── Styles ─────────────────────────────────────────────────
    const styles = document.createElement('style');
    styles.textContent = `
        #devtrack-widget-container * {
            margin: 0; padding: 0; box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        #devtrack-widget-btn {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 24px rgba(99, 102, 241, 0.4);
            z-index: 99999;
            transition: all 0.3s ease;
            animation: devtrack-pulse 2s ease-in-out infinite;
        }

        #devtrack-widget-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 32px rgba(99, 102, 241, 0.5);
        }

        @keyframes devtrack-pulse {
            0%, 100% { box-shadow: 0 4px 24px rgba(99, 102, 241, 0.4); }
            50% { box-shadow: 0 4px 32px rgba(99, 102, 241, 0.6); }
        }

        #devtrack-widget-btn svg {
            width: 28px; height: 28px; fill: white;
        }

        #devtrack-widget-window {
            position: fixed;
            bottom: 96px;
            right: 24px;
            width: 380px;
            height: 520px;
            background: #0d0d14;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 12px 48px rgba(0,0,0,0.5);
            z-index: 99998;
            display: none;
            flex-direction: column;
            overflow: hidden;
            animation: devtrack-slide-up 0.3s ease;
        }

        #devtrack-widget-window.open {
            display: flex;
        }

        @keyframes devtrack-slide-up {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .devtrack-header {
            padding: 16px 20px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .devtrack-header-avatar {
            width: 40px; height: 40px;
            border-radius: 12px;
            background: rgba(255,255,255,0.2);
            display: flex; align-items: center; justify-content: center;
            font-size: 1.2rem;
        }

        .devtrack-header-info h4 {
            font-size: 0.95rem; font-weight: 600;
        }

        .devtrack-header-info p {
            font-size: 0.75rem; opacity: 0.8;
        }

        .devtrack-close {
            margin-left: auto;
            background: none; border: none;
            color: white; cursor: pointer;
            font-size: 1.2rem; opacity: 0.7;
            transition: opacity 0.2s;
        }

        .devtrack-close:hover { opacity: 1; }

        .devtrack-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: #0d0d14;
        }

        .devtrack-msg {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 14px;
            font-size: 0.88rem;
            line-height: 1.5;
            animation: devtrack-msg-in 0.3s ease;
        }

        @keyframes devtrack-msg-in {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .devtrack-msg.bot {
            align-self: flex-start;
            background: #1a1a2e;
            color: #e0e0f0;
            border-bottom-left-radius: 4px;
        }

        .devtrack-msg.user {
            align-self: flex-end;
            background: #6366f1;
            color: white;
            border-bottom-right-radius: 4px;
        }

        .devtrack-msg.typing {
            background: #1a1a2e;
            color: #888;
        }

        .devtrack-typing-dots span {
            animation: devtrack-blink 1.4s infinite both;
            font-size: 1.2rem;
        }
        .devtrack-typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .devtrack-typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes devtrack-blink {
            0%, 80%, 100% { opacity: 0.3; }
            40% { opacity: 1; }
        }

        .devtrack-input-area {
            padding: 12px 16px;
            border-top: 1px solid rgba(255,255,255,0.06);
            display: flex;
            gap: 8px;
            background: #12121a;
        }

        .devtrack-input {
            flex: 1;
            padding: 10px 14px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            color: #f0f0f5;
            font-family: inherit;
            font-size: 0.88rem;
            outline: none;
            transition: border-color 0.2s;
        }

        .devtrack-input:focus {
            border-color: #6366f1;
        }

        .devtrack-input::placeholder { color: #555; }

        .devtrack-send {
            width: 40px; height: 40px;
            border-radius: 10px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }

        .devtrack-send:hover { transform: scale(1.05); }

        .devtrack-send svg {
            width: 18px; height: 18px;
            fill: none; stroke: white; stroke-width: 2;
        }

        .devtrack-powered {
            text-align: center;
            padding: 8px;
            font-size: 0.7rem;
            color: #444;
            background: #0d0d14;
        }

        .devtrack-powered a { color: #6366f1; text-decoration: none; }

        @media (max-width: 480px) {
            #devtrack-widget-window {
                width: calc(100vw - 16px);
                height: calc(100vh - 120px);
                right: 8px;
                bottom: 80px;
                border-radius: 12px;
            }
        }

        .devtrack-messages::-webkit-scrollbar { width: 4px; }
        .devtrack-messages::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }
    `;
    document.head.appendChild(styles);

    // ─── Build Widget HTML ──────────────────────────────────────
    const container = document.createElement('div');
    container.id = 'devtrack-widget-container';
    container.innerHTML = `
        <button id="devtrack-widget-btn" aria-label="Open chat">
            <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </button>
        <div id="devtrack-widget-window">
            <div class="devtrack-header">
                <div class="devtrack-header-avatar">🤖</div>
                <div class="devtrack-header-info">
                    <h4 id="devtrack-biz-name">AI Assistant</h4>
                    <p>Online • Typically replies instantly</p>
                </div>
                <button class="devtrack-close" id="devtrack-close">✕</button>
            </div>
            <div class="devtrack-messages" id="devtrack-messages">
                <div class="devtrack-msg bot">Hello! 👋 Welcome! How can I help you today?</div>
            </div>
            <div class="devtrack-input-area">
                <input type="text" class="devtrack-input" id="devtrack-input" placeholder="Type your message..." />
                <button class="devtrack-send" id="devtrack-send">
                    <svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                </button>
            </div>
            <div class="devtrack-powered">Powered by <a href="#" target="_blank">DevTrack AI</a></div>
        </div>
    `;
    document.body.appendChild(container);

    // ─── Event Handlers ─────────────────────────────────────────
    const btn = document.getElementById('devtrack-widget-btn');
    const win = document.getElementById('devtrack-widget-window');
    const closeBtn = document.getElementById('devtrack-close');
    const input = document.getElementById('devtrack-input');
    const sendBtn = document.getElementById('devtrack-send');
    const messagesDiv = document.getElementById('devtrack-messages');

    btn.addEventListener('click', () => {
        isOpen = !isOpen;
        win.classList.toggle('open', isOpen);
        if (isOpen) input.focus();
    });

    closeBtn.addEventListener('click', () => {
        isOpen = false;
        win.classList.remove('open');
    });

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // ─── Send Message ───────────────────────────────────────────
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Add user message
        addMessage(text, 'user');
        input.value = '';

        // Show typing indicator
        const typingEl = addTyping();

        try {
            const response = await fetch(`${apiBase}/chat/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    business_slug: businessSlug,
                    customer_id: customerId,
                    channel: 'web',
                }),
            });

            const data = await response.json();

            // Save customer ID for session continuity
            if (data.customer_id) {
                customerId = data.customer_id;
                localStorage.setItem('devtrack_widget_customer', customerId);
            }

            typingEl.remove();
            addMessage(data.response || 'Thanks for your message! How can I help?', 'bot');

        } catch (err) {
            typingEl.remove();
            // Fallback response when API is not available
            const fallbacks = [
                "Thank you for your message! I'm here to help. 😊",
                "I'd love to assist you with that! Could you tell me more?",
                "Great question! Let me look into that for you.",
                "Thanks for reaching out! We'll get back to you shortly.",
            ];
            addMessage(fallbacks[Math.floor(Math.random() * fallbacks.length)], 'bot');
        }
    }

    function addMessage(text, type) {
        const msg = document.createElement('div');
        msg.className = `devtrack-msg ${type}`;
        msg.textContent = text;
        messagesDiv.appendChild(msg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return msg;
    }

    function addTyping() {
        const typing = document.createElement('div');
        typing.className = 'devtrack-msg bot typing';
        typing.innerHTML = '<div class="devtrack-typing-dots"><span>.</span><span>.</span><span>.</span></div>';
        messagesDiv.appendChild(typing);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return typing;
    }

    // ─── Load Business Info ─────────────────────────────────────
    async function loadBusinessInfo() {
        try {
            const response = await fetch(`${apiBase}/chat/business/${businessSlug}`);
            if (response.ok) {
                businessInfo = await response.json();
                document.getElementById('devtrack-biz-name').textContent = businessInfo.name || 'AI Assistant';
                
                if (businessInfo.welcome_message) {
                    messagesDiv.innerHTML = `<div class="devtrack-msg bot">${businessInfo.welcome_message}</div>`;
                }
            }
        } catch (err) {
            // Use defaults
        }
    }

    loadBusinessInfo();
})();
