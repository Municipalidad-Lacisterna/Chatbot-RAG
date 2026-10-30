/**
 * Cisternin Chatbot Widget - Municipalidad de La Cisterna
 * Inserción autónoma para sitios web (React, Strapi, HTML, WordPress, etc.)
 * Uso: <script src="https://chatbot.lacisterna.cl/static/widget.js" defer></script>
 */
(function() {
  'use strict';

  // Evitar inyecciones duplicadas
  if (window.CisterninWidgetLoaded) return;
  window.CisterninWidgetLoaded = true;

  // Detectar la URL base del chatbot a partir del origen del script
  let baseUrl = "https://bot.aspenqlio.com";
  const scripts = document.getElementsByTagName('script');
  for (let s of scripts) {
    if (s.src && s.src.includes('widget.js')) {
      try {
        const u = new URL(s.src);
        baseUrl = u.origin;
      } catch (e) {}
      break;
    }
  }

  const chatUrl = `${baseUrl}/chat?v=20261028_v3`;
  const iconUrl = `${baseUrl}/static/cisternin.png`;

  // Estilos globales mínimos aislados
  const style = document.createElement('style');
  style.innerHTML = `
    #cisternin-widget-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    #cisternin-widget-btn {
      width: 62px;
      height: 62px;
      border-radius: 50%;
      background: #128C7E;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      border: 2px solid #25D366;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.25s ease, background 0.25s ease;
      outline: none;
      padding: 0;
    }
    #cisternin-widget-btn:hover {
      transform: scale(1.08);
      background: #25D366;
    }
    #cisternin-widget-btn img {
      width: 44px;
      height: 44px;
      object-fit: contain;
      border-radius: 50%;
      pointer-events: none;
    }
    #cisternin-widget-frame-box {
      display: none;
      position: fixed;
      bottom: 96px;
      right: 24px;
      width: 390px;
      height: 600px;
      max-width: calc(100vw - 32px);
      max-height: calc(100vh - 120px);
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      overflow: hidden;
      border: 1px solid rgba(0,0,0,0.12);
      z-index: 999999;
      background: #fff;
      animation: cisterninFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    #cisternin-widget-frame {
      width: 100%;
      height: 100%;
      border: none;
      display: block;
    }
    @keyframes cisterninFadeIn {
      from { opacity: 0; transform: translateY(16px) scale(0.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @media (max-width: 480px) {
      #cisternin-widget-frame-box {
        bottom: 0;
        right: 0;
        width: 100vw;
        height: 100vh;
        max-width: 100vw;
        max-height: 100vh;
        border-radius: 0;
      }
    }
  `;
  document.head.appendChild(style);

  // Contenedor principal
  const container = document.createElement('div');
  container.id = 'cisternin-widget-container';

  // Botón flotante
  const button = document.createElement('button');
  button.id = 'cisternin-widget-btn';
  button.title = 'Chatear con Cisternin';
  button.innerHTML = `<img src="${iconUrl}" alt="Cisternin">`;

  // Ventana flotante (iframe)
  const frameBox = document.createElement('div');
  frameBox.id = 'cisternin-widget-frame-box';

  let iframeCreated = false;
  let isOpen = false;

  function toggleChat() {
    isOpen = !isOpen;
    if (isOpen) {
      if (!iframeCreated) {
        const iframe = document.createElement('iframe');
        iframe.id = 'cisternin-widget-frame';
        iframe.src = chatUrl;
        iframe.title = 'Asistente Virtual Cisternin';
        iframe.allow = 'clipboard-write; microphone';
        frameBox.appendChild(iframe);
        iframeCreated = true;
      }
      frameBox.style.display = 'block';
      button.style.transform = 'scale(0.92)';
    } else {
      frameBox.style.display = 'none';
      button.style.transform = 'scale(1)';
    }
  }

  button.addEventListener('click', toggleChat);

  container.appendChild(button);
  document.body.appendChild(container);
  document.body.appendChild(frameBox);

  // Exponer API global opcional
  window.CisterninChat = {
    open: function() { if (!isOpen) toggleChat(); },
    close: function() { if (isOpen) toggleChat(); },
    toggle: toggleChat
  };
})();
