(function () {
  const getCookie = (name) => {
    const cookies = document.cookie ? document.cookie.split("; ") : [];
    for (const c of cookies) {
      const idx = c.indexOf("=");
      if (idx === -1) continue;
      const k = c.slice(0, idx);
      const v = c.slice(idx + 1);
      if (k === name) return decodeURIComponent(v);
    }
    return "";
  };
  const csrfToken = () => getCookie("csrftoken") || "";

  const newConversationId = () => {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return "conv-" + Math.random().toString(16).slice(2) + Date.now().toString(16);
  };
  const sessionStore = (() => {
    try {
      const probeKey = "__helper_widget_probe__";
      window.sessionStorage.setItem(probeKey, "1");
      window.sessionStorage.removeItem(probeKey);
      return window.sessionStorage;
    } catch (_err) {
      return null;
    }
  })();
  const hashString = (input) => {
    let hash = 0;
    const text = String(input || "");
    for (let i = 0; i < text.length; i += 1) {
      hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
    }
    return hash.toString(16).padStart(8, "0");
  };
  const normalizeLanguageCode = (raw) => {
    const value = String(raw || "").trim().toLowerCase().replace("_", "-");
    if (!value) return "en";
    const primary = value.split("-", 1)[0];
    if (primary === "es" || primary === "so") return primary;
    return "en";
  };
  const WIDGET_COPY = {
    en: {
      summaryOpen: "Open helper",
      summaryResume: "Resume helper",
      contextFresh: "Follow-up questions stay in one lesson thread in this browser session until you reset chat.",
      contextResume: "Conversation context is saved for this lesson in this browser session until you reset chat.",
      turnStudent: "You",
      turnAssistant: "Helper",
      followupsLabel: "Try next:",
      resetStatus: "Conversation reset.",
      emptyMessage: "Type a question before asking.",
      thinking: "Thinking...",
      noOutput: "(no output)",
      networkFailure: "Helper error: network_failure",
      quickTitle: "Quick asks (tap to send):",
      quickAriaLabel: "Quick helper prompts",
      inputLabel: "Question for helper",
      inputPlaceholder: "Ask for help...",
      askButton: "Ask",
      resetButton: "Reset chat",
      citationsTitle: "Lesson references used",
      errorPrefix: "Helper error",
      promptSets: {
        piper: [
          {
            label: "Jump not working",
            prompt: "In StoryMode, left/right work but jump does not work in Cheeseteroid. Help me troubleshoot one step at a time.",
          },
          {
            label: "No buttons respond",
            prompt: "None of my StoryMode breadboard buttons are responding. Give me one check at a time and ask me to retest.",
          },
          {
            label: "One direction fails",
            prompt: "Only one movement direction fails on my Piper controls. What should I compare first in my jumper wiring path?",
          },
          {
            label: "Mouse-only path",
            prompt: "I only have a mouse right now, no keyboard. What is the mouse-first path for this lesson?",
          },
          {
            label: "Upload .sb3 help",
            prompt: "I finished but cannot find my .sb3 file to upload. Walk me through check -> retest steps.",
          },
        ],
        scratch: [
          {
            label: "Sprite won't move",
            prompt: "My sprite does not move when I click the green flag. Please give me one Scratch block check at a time.",
          },
          {
            label: "Backdrop won't change",
            prompt: "My backdrop never changes. What is one specific Scratch block check I should do first?",
          },
          {
            label: "Score not updating",
            prompt: "My score is not updating correctly. Help me debug in small steps and retest after each change.",
          },
          {
            label: "Game over missing",
            prompt: "My game over condition does not trigger. Give me one event/broadcast check and then ask me to retest.",
          },
          {
            label: "Save and upload",
            prompt: "Please walk me through saving my Scratch project as .sb3 and uploading it privately.",
          },
        ],
        general: [
          {
            label: "What is today's goal?",
            prompt: "What is the goal for this lesson, and what should be done first?",
          },
          {
            label: "I am stuck",
            prompt: "I am stuck. Ask me one clarifying question, then give me one small next step.",
          },
          {
            label: "How to ask better",
            prompt: "Help me write a clear help request: what I expected, what happened, and what I already tried.",
          },
        ],
      },
    },
    es: {
      summaryOpen: "Abrir ayudante",
      summaryResume: "Continuar ayudante",
      contextFresh: "Las preguntas de seguimiento se quedan en un solo hilo de esta leccion en esta sesion del navegador hasta que reinicies el chat.",
      contextResume: "El contexto de la conversacion se guarda para esta leccion en esta sesion del navegador hasta que reinicies el chat.",
      turnStudent: "Tu",
      turnAssistant: "Ayudante",
      followupsLabel: "Prueba despues:",
      resetStatus: "Conversacion reiniciada.",
      emptyMessage: "Escribe una pregunta antes de pedir ayuda.",
      thinking: "Pensando...",
      noOutput: "(sin respuesta)",
      networkFailure: "Error del ayudante: network_failure",
      quickTitle: "Preguntas rapidas (toca para enviar):",
      quickAriaLabel: "Preguntas rapidas del ayudante",
      inputLabel: "Pregunta para el ayudante",
      inputPlaceholder: "Pide ayuda...",
      askButton: "Preguntar",
      resetButton: "Reiniciar chat",
      citationsTitle: "Referencias de la leccion usadas",
      errorPrefix: "Error del ayudante",
      promptSets: {
        piper: [
          {
            label: "Salto no funciona",
            prompt: "En StoryMode, izquierda y derecha funcionan pero saltar no funciona en Cheeseteroid. Ayudame a revisar un paso a la vez.",
          },
          {
            label: "Ningun boton responde",
            prompt: "Ninguno de mis botones del breadboard en StoryMode responde. Dame una comprobacion a la vez y pideme volver a probar.",
          },
          {
            label: "Una direccion falla",
            prompt: "Solo falla una direccion de movimiento en mis controles de Piper. Que debo comparar primero en la ruta de cableado de mis jumpers?",
          },
          {
            label: "Ruta solo con mouse",
            prompt: "Solo tengo un mouse ahora, no teclado. Cual es la ruta pensada para mouse en esta leccion?",
          },
          {
            label: "Ayuda con .sb3",
            prompt: "Ya termine pero no encuentro mi archivo .sb3 para subirlo. Guiame con pasos de revisar y volver a probar.",
          },
        ],
        scratch: [
          {
            label: "El sprite no se mueve",
            prompt: "Mi sprite no se mueve cuando hago clic en la bandera verde. Dame una sola comprobacion de bloques de Scratch a la vez.",
          },
          {
            label: "El fondo no cambia",
            prompt: "Mi fondo nunca cambia. Cual es una comprobacion especifica de Scratch que debo hacer primero?",
          },
          {
            label: "La puntuacion no cambia",
            prompt: "Mi puntuacion no se actualiza bien. Ayudame a depurarlo en pasos pequenos y a volver a probar despues de cada cambio.",
          },
          {
            label: "Falta game over",
            prompt: "Mi condicion de game over no se activa. Dame una comprobacion de evento o broadcast y luego pideme volver a probar.",
          },
          {
            label: "Guardar y subir",
            prompt: "Guiame para guardar mi proyecto de Scratch como .sb3 y subirlo de forma privada.",
          },
        ],
        general: [
          {
            label: "Cual es la meta de hoy?",
            prompt: "Cual es la meta de esta leccion y que deberia hacer primero?",
          },
          {
            label: "Estoy atorado",
            prompt: "Estoy atorado. Hazme una pregunta de aclaracion y luego dame un siguiente paso pequeno.",
          },
          {
            label: "Como pedir mejor ayuda",
            prompt: "Ayudame a escribir una solicitud de ayuda clara: que esperaba, que paso y que ya intente.",
          },
        ],
      },
    },
    so: {
      summaryOpen: "Fur caawiye",
      summaryResume: "Sii wad caawiye",
      contextFresh: "Su'aalaha daba socda waxay ku sii jiraan hal xadhig oo casharkan ah inta lagu jiro session-kan browser-ka ilaa aad dib u dejiso chat-ka.",
      contextResume: "Xogta wada hadalka waxaa loogu kaydiyaa casharkan session-kan browser-ka ilaa aad dib u dejiso chat-ka.",
      turnStudent: "Adiga",
      turnAssistant: "Caawiye",
      followupsLabel: "Ku xigso tan:",
      resetStatus: "Wada hadalka dib ayaa loo dejiyay.",
      emptyMessage: "Qor su'aal ka hor intaadan caawimo codsan.",
      thinking: "Wuu fikirayaa...",
      noOutput: "(jawaab ma jirto)",
      networkFailure: "Khalad caawiye: network_failure",
      quickTitle: "Su'aalo degdeg ah (taabo si aad u dirto):",
      quickAriaLabel: "Su'aalaha degdega ah ee caawiyaha",
      inputLabel: "Su'aal u dir caawiyaha",
      inputPlaceholder: "Caawimo codso...",
      askButton: "Weydii",
      resetButton: "Dib u deji chat-ka",
      citationsTitle: "Tixraacyada casharka ee la isticmaalay",
      errorPrefix: "Khalad caawiye",
      promptSets: {
        piper: [
          {
            label: "Jump ma shaqeeyo",
            prompt: "StoryMode gudaheeda, bidix iyo midig way shaqeeyaan laakiin jump-ku kama shaqeeyo Cheeseteroid. Iga caawi hal talaabo markiiba.",
          },
          {
            label: "Badhamo ma jawaabaan",
            prompt: "Midkoodna badhamadayda StoryMode breadboard-ka ma jawaabaan. I sii hal hubin markiiba oo iga codso inaan mar kale tijaabiyo.",
          },
          {
            label: "Hal jiho ayaa fashilanta",
            prompt: "Kaliya hal jiho dhaqdhaqaaq ayaa ka fashilanta kontarooladayda Piper. Maxaan marka hore isbarbar dhigaa jidka fiilooyinka jumper-ka?",
          },
          {
            label: "Waddo mouse keliya",
            prompt: "Hadda waxaan haystaa mouse keliya, keyboard ma hayo. Waa maxay waddada mouse-ku hormarinayo ee casharkan?",
          },
          {
            label: "Caawimo .sb3",
            prompt: "Waan dhammeeyay laakiin ma heli karo faylkayga .sb3 si aan u geliyo. Igu hag tallaabooyin hubi kadibna mar kale tijaabi.",
          },
        ],
        scratch: [
          {
            label: "Sprite-ku ma socdo",
            prompt: "Sprite-kaygu ma socdo marka aan gujiyo green flag-ka. I sii hal hubin oo Scratch block ah markiiba.",
          },
          {
            label: "Backdrop ma beddelmo",
            prompt: "Backdrop-kaygu waligiis ma beddelmo. Waa maxay hal hubin oo Scratch ah oo gaar ah oo aan marka hore sameeyo?",
          },
          {
            label: "Score-ku ma cusboona",
            prompt: "Score-kaygu si sax ah uma cusboona. Iga caawi inaan khalad-saaro anigoo qaadaya tallaabooyin yaryar oo aan mar kasta dib u tijaabiyo.",
          },
          {
            label: "Game over ma muuqdo",
            prompt: "Shuruuddayda game over ma shaqeyso. I sii hal hubin oo event ama broadcast ah ka dibna iga codso inaan mar kale tijaabiyo.",
          },
          {
            label: "Kaydi oo geli",
            prompt: "Ii sharax sida aan mashruucayga Scratch ugu kaydiyo .sb3 oo aan si gaar ah ugu geliyo.",
          },
        ],
        general: [
          {
            label: "Waa maxay yoolka maanta?",
            prompt: "Waa maxay yoolka casharkan, maxaase ugu horeyn la sameeyaa?",
          },
          {
            label: "Waan ku xannibanahay",
            prompt: "Waan ku xannibanahay. I weydii hal su'aal oo caddayn ah ka dibna i sii hal tallaabo oo yar.",
          },
          {
            label: "Sideen si fiican u codsadaa caawimo",
            prompt: "Iga caawi inaan qoro codsi caawimo oo cad: waxa aan filayay, waxa dhacay, iyo waxa aan hore u tijaabiyay.",
          },
        ],
      },
    },
  };

  const widgets = document.querySelectorAll(".helper-widget");

  const hasKeyword = (text, words) => words.some((w) => text.includes(w));
  const helperErrorCodeFromStatus = (status) => {
    if (status === 400) return "bad_request";
    if (status === 401) return "unauthorized";
    if (status === 403) return "csrf_forbidden";
    if (status === 404) return "not_found";
    if (status === 429) return "rate_limited";
    if (status >= 500 && status < 600) return "backend_error";
    return `http_${status}`;
  };
  const formatHelperErrorText = ({ status, data, headerRequestId, copy }) => {
    const errorCode = data && typeof data.error === "string" ? data.error : helperErrorCodeFromStatus(status);
    const requestId =
      (data && typeof data.request_id === "string" && data.request_id) || headerRequestId || "";
    let text = `${copy.errorPrefix}: ${errorCode}`;
    if (requestId) {
      text += ` (request ${requestId})`;
    }
    if (data && typeof data.message === "string" && data.message.trim()) {
      text += `. ${data.message.trim()}`;
    }
    return text;
  };
  const detectPromptGroup = (ref, context, topics) => {
    const meta = `${ref} ${context} ${topics}`.toLowerCase();
    if (
      hasKeyword(meta, [
        "piper",
        "storymode",
        "pipercode",
        "mars",
        "cheeseteroid",
        "gpio",
        "breadboard",
        "jumper",
        "wiring",
      ])
    ) {
      return "piper";
    }
    if (hasKeyword(meta, ["scratch", "sprite", "backdrop", "animation", "game"])) {
      return "scratch";
    }
    return "general";
  };

  widgets.forEach((widget, idx) => {
    const summaryHint = widget.querySelector(".helper-shell-summary-hint");
    const label = widget.querySelector(".helper-label");
    const textarea = widget.querySelector(".helper-input");
    const button = widget.querySelector(".helper-submit");
    const resetButton = widget.querySelector(".helper-reset");
    const output = widget.querySelector(".helper-output");
    const transcript = widget.querySelector(".helper-transcript");
    const contextNote = widget.querySelector(".helper-context-note");
    const citationWrap = widget.querySelector(".helper-citations");
    const citationList = widget.querySelector(".helper-citations-list");
    const citationsTitle = widget.querySelector(".helper-citations-title");
    const quickWrap = widget.querySelector(".helper-quick-wrap");
    const quickTitle = widget.querySelector(".helper-quick-title");
    const quickActions = widget.querySelector(".helper-quick-actions");
    const inputId = `helper-input-${idx}`;
    textarea.id = inputId;
    label.setAttribute("for", inputId);
    const scopeToken = (widget.dataset.helperScopeToken || "").trim();
    const helperReference = (widget.dataset.helperReference || "").trim();
    const helperContext = (widget.dataset.helperContext || "").trim();
    const helperTopics = (widget.dataset.helperTopics || "").trim();
    const helperLanguageCode = normalizeLanguageCode((widget.dataset.helperLanguageCode || "en").trim() || "en");
    const activeCopy = WIDGET_COPY[helperLanguageCode] || WIDGET_COPY.en;
    const storageKey = `helper-widget:${hashString(
      [window.location.pathname, helperReference, helperContext, helperTopics, helperLanguageCode, scopeToken].join("|")
    )}`;
    let transcriptTurns = [];
    let latestCitations = [];
    let conversationId = newConversationId();

    const loadState = () => {
      if (!sessionStore) return null;
      try {
        const raw = sessionStore.getItem(storageKey);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object") return null;
        return parsed;
      } catch (_err) {
        return null;
      }
    };

    const saveState = () => {
      if (!sessionStore) return;
      try {
        sessionStore.setItem(
          storageKey,
          JSON.stringify({
            conversationId,
            turns: transcriptTurns,
            citations: latestCitations,
            draft: textarea.value || "",
          })
        );
      } catch (_err) {
        // Best-effort only.
      }
    };

    const updateConversationChrome = () => {
      const hasHistory = transcriptTurns.length > 0;
      if (summaryHint) {
        summaryHint.textContent = hasHistory ? activeCopy.summaryResume : activeCopy.summaryOpen;
      }
      if (contextNote) {
        contextNote.textContent = hasHistory
          ? activeCopy.contextResume
          : activeCopy.contextFresh;
      }
    };

    const setOutput = (txt) => {
      output.textContent = txt;
    };

    const renderTurn = (turnData) => {
      if (!transcript) return;
      const role = turnData && turnData.role === "student" ? "student" : "assistant";
      const text = turnData && typeof turnData.text === "string" ? turnData.text : "";
      const suggestions = Array.isArray(turnData && turnData.suggestions) ? turnData.suggestions : [];
      const turn = document.createElement("div");
      turn.className = `helper-turn helper-turn--${role === "student" ? "student" : "assistant"}`;
      const labelNode = document.createElement("span");
      labelNode.className = "helper-turn-label";
      labelNode.textContent = role === "student" ? activeCopy.turnStudent : activeCopy.turnAssistant;
      const contentNode = document.createElement("div");
      contentNode.textContent = text;
      turn.appendChild(labelNode);
      turn.appendChild(contentNode);
      if (role !== "student" && suggestions.length) {
        const followupsWrap = document.createElement("div");
        followupsWrap.className = "helper-followups";
        const followupsLabel = document.createElement("div");
        followupsLabel.className = "helper-followups-label";
        followupsLabel.textContent = activeCopy.followupsLabel;
        followupsWrap.appendChild(followupsLabel);
        suggestions.forEach((row) => {
          const suggestion = String(row || "").trim();
          if (!suggestion) return;
          const followupBtn = document.createElement("button");
          followupBtn.type = "button";
          followupBtn.className = "helper-followup-action";
          followupBtn.textContent = suggestion;
          followupBtn.addEventListener("click", () => {
            if (button.disabled) return;
            textarea.value = suggestion;
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
            sendMessage(suggestion);
          });
          followupsWrap.appendChild(followupBtn);
        });
        if (followupsWrap.childElementCount > 1) {
          turn.appendChild(followupsWrap);
        }
      }
      transcript.appendChild(turn);
      transcript.scrollTop = transcript.scrollHeight;
    };

    const appendTurn = (role, text, options = {}) => {
      const turnData = {
        role: role === "student" ? "student" : "assistant",
        text: String(text || ""),
        suggestions: Array.isArray(options.suggestions)
          ? options.suggestions.map((row) => String(row || "").trim()).filter(Boolean)
          : [],
      };
      transcriptTurns.push(turnData);
      renderTurn(turnData);
      updateConversationChrome();
      saveState();
    };

    const clearTranscript = () => {
      if (!transcript) return;
      transcript.innerHTML = "";
      transcriptTurns = [];
      latestCitations = [];
      renderCitations([]);
      setOutput(activeCopy.resetStatus);
      conversationId = newConversationId();
      textarea.value = "";
      updateConversationChrome();
      saveState();
    };

    const renderCitations = (rows) => {
      if (!citationWrap || !citationList) return;
      const citations = Array.isArray(rows) ? rows : [];
      latestCitations = citations.map((row) => ({
        id: row && row.id ? String(row.id) : "",
        text: row && row.text ? String(row.text) : "",
        source: row && row.source ? String(row.source) : "",
      }));
      citationList.innerHTML = "";
      if (!citations.length) {
        citationWrap.hidden = true;
        saveState();
        return;
      }
      citations.forEach((row) => {
        const li = document.createElement("li");
        const refId = row && row.id ? String(row.id) : "";
        const text = row && row.text ? String(row.text) : "";
        const source = row && row.source ? String(row.source) : "";
        const parts = [];
        if (refId) parts.push(`[${refId}]`);
        if (source) parts.push(`${source}:`);
        parts.push(text);
        li.textContent = parts.join(" ");
        citationList.appendChild(li);
      });
      citationWrap.hidden = false;
      saveState();
    };

    const setControlsBusy = (disabled) => {
      button.disabled = disabled;
      if (disabled) {
        button.setAttribute("aria-busy", "true");
      } else {
        button.removeAttribute("aria-busy");
      }
      if (resetButton) {
        resetButton.disabled = disabled;
      }
      if (!quickActions) return;
      quickActions.querySelectorAll(".helper-quick-action").forEach((quickBtn) => {
        quickBtn.disabled = disabled;
      });
      if (!transcript) return;
      transcript.querySelectorAll(".helper-followup-action").forEach((followupBtn) => {
        followupBtn.disabled = disabled;
      });
    };

    const sendMessage = async (rawMessage) => {
      const message = (rawMessage || "").trim();
      if (!message) {
        setOutput(activeCopy.emptyMessage);
        renderCitations([]);
        return;
      }
      textarea.value = message;
      appendTurn("student", message);
      setControlsBusy(true);
      setOutput(activeCopy.thinking);

      try {
        const payload = {
          message,
          conversation_id: conversationId,
          language_code: helperLanguageCode,
        };
        if (scopeToken) {
          payload.scope_token = scopeToken;
        }

        const res = await fetch("/helper/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
          },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        });

        let data = null;
        const contentType = (res.headers.get("Content-Type") || "").toLowerCase();
        if (contentType.includes("application/json")) {
          try {
            data = await res.json();
          } catch (_err) {
            data = null;
          }
        }

        if (data && typeof data.conversation_id === "string" && data.conversation_id.trim()) {
          conversationId = data.conversation_id.trim();
        }

        if (!res.ok) {
          const requestIdHeader = (res.headers.get("X-Request-ID") || "").trim();
          const errorText = formatHelperErrorText({
            status: res.status,
            data,
            headerRequestId: requestIdHeader,
            copy: activeCopy,
          });
          appendTurn("assistant", errorText);
          setOutput(errorText);
          renderCitations([]);
          return;
        }

        const responseText = (data && data.text) || activeCopy.noOutput;
        const followUpSuggestions = (data && data.follow_up_suggestions) || [];
        appendTurn("assistant", responseText, { suggestions: followUpSuggestions });
        textarea.value = "";
        setOutput("");
        renderCitations((data && data.citations) || []);
        textarea.focus();
      } catch (_err) {
        const errText = activeCopy.networkFailure;
        appendTurn("assistant", errText);
        setOutput(errText);
        renderCitations([]);
      } finally {
        setControlsBusy(false);
      }
    };

    const promptGroup = detectPromptGroup(helperReference, helperContext, helperTopics);
    const promptSet = activeCopy.promptSets[promptGroup] || activeCopy.promptSets.general;
    if (label) {
      label.textContent = activeCopy.inputLabel;
    }
    if (textarea) {
      textarea.placeholder = activeCopy.inputPlaceholder;
    }
    if (button) {
      button.textContent = activeCopy.askButton;
    }
    if (resetButton) {
      resetButton.textContent = activeCopy.resetButton;
    }
    if (quickTitle) {
      quickTitle.textContent = activeCopy.quickTitle;
    }
    if (quickActions) {
      quickActions.setAttribute("aria-label", activeCopy.quickAriaLabel);
    }
    if (citationsTitle) {
      citationsTitle.textContent = activeCopy.citationsTitle;
    }
    if (quickActions && promptSet.length) {
      promptSet.forEach((item) => {
        const quickBtn = document.createElement("button");
        quickBtn.type = "button";
        quickBtn.className = "helper-quick-action";
        quickBtn.textContent = item.label;
        quickBtn.addEventListener("click", () => {
          if (button.disabled) return;
          textarea.value = item.prompt;
          textarea.focus();
          textarea.setSelectionRange(textarea.value.length, textarea.value.length);
          sendMessage(item.prompt);
        });
        quickActions.appendChild(quickBtn);
      });
    } else if (quickWrap) {
      quickWrap.hidden = true;
    }

    const restored = loadState();
    if (restored && typeof restored.conversationId === "string" && restored.conversationId.trim()) {
      conversationId = restored.conversationId.trim();
    }
    if (restored && typeof restored.draft === "string") {
      textarea.value = restored.draft;
    }
    if (restored && Array.isArray(restored.turns) && transcript) {
      transcriptTurns = restored.turns
        .map((row) => ({
          role: row && row.role === "student" ? "student" : "assistant",
          text: row && typeof row.text === "string" ? row.text : "",
          suggestions: Array.isArray(row && row.suggestions)
            ? row.suggestions.map((item) => String(item || "").trim()).filter(Boolean)
            : [],
        }))
        .filter((row) => row.text);
      transcriptTurns.forEach((row) => renderTurn(row));
    }
    if (restored && Array.isArray(restored.citations)) {
      renderCitations(restored.citations);
    }
    updateConversationChrome();
    textarea.addEventListener("input", () => {
      saveState();
    });

    button.addEventListener("click", async () => {
      await sendMessage(textarea.value || "");
    });

    if (resetButton) {
      resetButton.addEventListener("click", () => {
        if (button.disabled) return;
        clearTranscript();
      });
    }
  });
})();
