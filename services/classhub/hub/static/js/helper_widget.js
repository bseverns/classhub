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

  const widgets = document.querySelectorAll(".helper-widget");
  const QUICK_PROMPTS = {
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
  };

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
  const formatHelperErrorText = ({ status, data, headerRequestId }) => {
    const errorCode = data && typeof data.error === "string" ? data.error : helperErrorCodeFromStatus(status);
    const requestId =
      (data && typeof data.request_id === "string" && data.request_id) || headerRequestId || "";
    let text = `Helper error: ${errorCode}`;
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
    const label = widget.querySelector(".helper-label");
    const textarea = widget.querySelector(".helper-input");
    const button = widget.querySelector(".helper-submit");
    const output = widget.querySelector(".helper-output");
    const citationWrap = widget.querySelector(".helper-citations");
    const citationList = widget.querySelector(".helper-citations-list");
    const quickWrap = widget.querySelector(".helper-quick-wrap");
    const quickActions = widget.querySelector(".helper-quick-actions");
    const inputId = `helper-input-${idx}`;
    textarea.id = inputId;
    label.setAttribute("for", inputId);
    const scopeToken = (widget.dataset.helperScopeToken || "").trim();
    const helperReference = (widget.dataset.helperReference || "").trim();
    const helperContext = (widget.dataset.helperContext || "").trim();
    const helperTopics = (widget.dataset.helperTopics || "").trim();

    const setOutput = (txt) => {
      output.textContent = txt;
    };
    const renderCitations = (rows) => {
      if (!citationWrap || !citationList) return;
      const citations = Array.isArray(rows) ? rows : [];
      citationList.innerHTML = "";
      if (!citations.length) {
        citationWrap.hidden = true;
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
    };

    const setQuickActionsBusy = (disabled) => {
      if (!quickActions) return;
      quickActions.querySelectorAll(".helper-quick-action").forEach((quickBtn) => {
        quickBtn.disabled = disabled;
      });
    };

    const sendMessage = async (rawMessage) => {
      const message = (rawMessage || "").trim();
      if (!message) {
        setOutput("Type a question before asking.");
        renderCitations([]);
        return;
      }
      textarea.value = message;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      setQuickActionsBusy(true);
      setOutput("Thinking…");
      try {
        const payload = { message };
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
        if (!res.ok) {
          const requestIdHeader = (res.headers.get("X-Request-ID") || "").trim();
          setOutput(
            formatHelperErrorText({
              status: res.status,
              data,
              headerRequestId: requestIdHeader,
            }),
          );
          renderCitations([]);
          return;
        }
        setOutput((data && data.text) || "(no output)");
        renderCitations((data && data.citations) || []);
      } catch (err) {
        setOutput("Helper error: network_failure");
        renderCitations([]);
      } finally {
        button.disabled = false;
        button.removeAttribute("aria-busy");
        setQuickActionsBusy(false);
      }
    };

    const promptGroup = detectPromptGroup(helperReference, helperContext, helperTopics);
    const promptSet = QUICK_PROMPTS[promptGroup] || QUICK_PROMPTS.general;
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

    button.addEventListener("click", async () => {
      await sendMessage(textarea.value || "");
    });
  });
})();
