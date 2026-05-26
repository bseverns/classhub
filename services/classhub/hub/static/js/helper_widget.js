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
    if (primary === "es" || primary === "so" || primary === "ksw") return primary;
    return "en";
  };
  const parsePromptSets = (widget) => {
    const payload = widget.querySelector(".helper-prompt-sets-json");
    if (!payload) return {};
    try {
      const parsed = JSON.parse(payload.textContent || "{}");
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_err) {
      return {};
    }
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
    const shell = widget.querySelector(".helper-shell");
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
    const readI18n = (key, fallback) => {
      const value = String(widget.getAttribute(`data-i18n-${key}`) || "").trim();
      return value || fallback;
    };
    const chromeCopy = {
      summaryOpen: readI18n("summary-open", "Open helper"),
      summaryResume: readI18n("summary-resume", "Resume helper"),
      contextFresh: readI18n(
        "context-fresh",
        "Follow-up questions stay in one lesson thread in this browser session until you reset chat.",
      ),
      contextResume: readI18n(
        "context-resume",
        "Conversation context is saved for this lesson in this browser session until you reset chat.",
      ),
      turnStudent: readI18n("turn-student", "You"),
      turnAssistant: readI18n("turn-assistant", "Helper"),
      followupsLabel: readI18n("followups-label", "Try next:"),
      resetStatus: readI18n("reset-status", "Conversation reset."),
      emptyMessage: readI18n("empty-message", "Type a question before asking."),
      thinking: readI18n("thinking", "Thinking..."),
      noOutput: readI18n("no-output", "(no output)"),
      networkFailure: readI18n("network-failure", "Helper error: network_failure"),
      quickTitle: readI18n("quick-title", "Quick asks (tap to send):"),
      quickAriaLabel: readI18n("quick-aria-label", "Quick helper prompts"),
      inputLabel: readI18n("input-label", "Question for helper"),
      inputPlaceholder: readI18n("input-placeholder", "Ask for help..."),
      askButton: readI18n("ask-button", "Ask"),
      resetButton: readI18n("reset-button", "Reset chat"),
      citationsTitle: readI18n("citations-title", "Lesson references used"),
      errorPrefix: readI18n("error-prefix", "Helper error"),
    };
    const promptSets = parsePromptSets(widget);
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
            open: shell ? Boolean(shell.open) : false,
          })
        );
      } catch (_err) {
        // Best-effort only.
      }
    };

    const updateConversationChrome = () => {
      const hasHistory = transcriptTurns.length > 0;
      if (summaryHint) {
        summaryHint.textContent = hasHistory ? chromeCopy.summaryResume : chromeCopy.summaryOpen;
      }
      if (contextNote) {
        contextNote.textContent = hasHistory
          ? chromeCopy.contextResume
          : chromeCopy.contextFresh;
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
      labelNode.textContent = role === "student" ? chromeCopy.turnStudent : chromeCopy.turnAssistant;
      const contentNode = document.createElement("div");
      contentNode.textContent = text;
      turn.appendChild(labelNode);
      turn.appendChild(contentNode);
      if (role !== "student" && suggestions.length) {
        const followupsWrap = document.createElement("div");
        followupsWrap.className = "helper-followups";
        const followupsLabel = document.createElement("div");
        followupsLabel.className = "helper-followups-label";
        followupsLabel.textContent = chromeCopy.followupsLabel;
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
      setOutput(chromeCopy.resetStatus);
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
        setOutput(chromeCopy.emptyMessage);
        renderCitations([]);
        return;
      }
      textarea.value = message;
      appendTurn("student", message);
      setControlsBusy(true);
      setOutput(chromeCopy.thinking);

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
            copy: chromeCopy,
          });
          appendTurn("assistant", errorText);
          setOutput(errorText);
          renderCitations([]);
          return;
        }

        const responseText = (data && data.text) || chromeCopy.noOutput;
        const followUpSuggestions = (data && data.follow_up_suggestions) || [];
        appendTurn("assistant", responseText, { suggestions: followUpSuggestions });
        textarea.value = "";
        setOutput("");
        renderCitations((data && data.citations) || []);
        textarea.focus();
      } catch (_err) {
        const errText = chromeCopy.networkFailure;
        appendTurn("assistant", errText);
        setOutput(errText);
        renderCitations([]);
      } finally {
        setControlsBusy(false);
      }
    };

    const promptGroup = detectPromptGroup(helperReference, helperContext, helperTopics);
    const promptSet = promptSets[promptGroup] || promptSets.general;
    if (label) {
      label.textContent = chromeCopy.inputLabel;
    }
    if (textarea) {
      textarea.placeholder = chromeCopy.inputPlaceholder;
    }
    if (button) {
      button.textContent = chromeCopy.askButton;
    }
    if (resetButton) {
      resetButton.textContent = chromeCopy.resetButton;
    }
    if (quickTitle) {
      quickTitle.textContent = chromeCopy.quickTitle;
    }
    if (quickActions) {
      quickActions.setAttribute("aria-label", chromeCopy.quickAriaLabel);
    }
    if (citationsTitle) {
      citationsTitle.textContent = chromeCopy.citationsTitle;
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
    if (shell && restored && typeof restored.open === "boolean") {
      shell.open = restored.open;
    }
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

    if (shell) {
      shell.addEventListener("toggle", () => {
        saveState();
      });
    }

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
