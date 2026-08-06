/** Visitor chat page.
 *
 * - Keep-chat cookie holds the conversation_id; Reset mints a new one.
 * - Sending streams the Avatar's reply over SSE (tokens + tool-status).
 * - A 10s poll (easing to 60s after 5 quiet minutes) picks up the human's
 *   async messages posted from /admin.
 * - Bare `Qn` is an instant FAQ answer; `?q=N` deep-links auto-submit it.
 * - The composer autofocuses on load and refocuses after every send.
 */

import { getConfig, getConversation, type Message } from "../lib/api";
import { getCookie, setCookie } from "../lib/cookies";
import {
  createMessageEl,
  createToolStatusEl,
  dayKey,
  dayLabel,
  formatTime,
  initialsFor,
  markToolStatusDone,
} from "../lib/messages";
import { renderMarkdown } from "../lib/markdown";
import { BlockedError, NameRequiredError, RateLimitError, streamChat } from "../lib/sse";
import { initTheme } from "../lib/theme";
import { maybeStartTour } from "./tour";

const CID_COOKIE = "avatar_cid";
const KEEP_COOKIE = "avatar_keep";
const NAME_KEY = "avatar-name";

const SUGGESTIONS = [
  "What do you do?",
  "What's your professional background?",
  "Can I get in touch with the real you?",
];

const convo = document.getElementById("convo") as HTMLElement;
const messagesEl = document.getElementById("messages") as HTMLElement;
const intro = document.getElementById("intro") as HTMLElement;
const typing = document.getElementById("typing") as HTMLElement;
const composerInput = document.getElementById("composerInput") as HTMLTextAreaElement;
const sendBtn = document.getElementById("sendBtn") as HTMLButtonElement;
const nameField = document.getElementById("nameField") as HTMLInputElement;
const nameFieldWrap = nameField.closest(".name-field") as HTMLElement;
const keepChat = document.getElementById("keepChat") as HTMLInputElement;
const resetBtn = document.getElementById("resetBtn") as HTMLButtonElement;
const suggestRow = document.getElementById("suggestRow") as HTMLElement;
const attnBtn = document.getElementById("attnBtn") as HTMLButtonElement;

let conversationId = "";
let lastMessageId = 0;
let lastDay: string | null = null;
let lastActivity = Date.now();
let sending = false;
let pollTimer: number | undefined;

init();

async function init(): Promise<void> {
  initTheme();
  nameField.value = localStorage.getItem(NAME_KEY) ?? "";
  nameField.addEventListener("change", () =>
    localStorage.setItem(NAME_KEY, nameField.value.trim()),
  );
  nameFieldWrap.addEventListener("animationend", () => nameFieldWrap.classList.remove("is-error"));

  keepChat.checked = getCookie(KEEP_COOKIE) !== "0";
  keepChat.addEventListener("change", () => {
    setCookie(KEEP_COOKIE, keepChat.checked ? "1" : "0");
    if (keepChat.checked) setCookie(CID_COOKIE, conversationId);
  });

  resetBtn.addEventListener("click", resetChat);

  for (const text of SUGGESTIONS) {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.textContent = text;
    chip.addEventListener("click", () => void send(text));
    suggestRow.appendChild(chip);
  }

  composerInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(composerInput.value);
    }
  });
  composerInput.addEventListener("input", autoGrow);
  sendBtn.addEventListener("click", () => void send(composerInput.value));
  attnBtn.addEventListener("click", () => {
    const on = attnBtn.classList.toggle("is-on");
    attnBtn.setAttribute("aria-pressed", String(on));
    composerInput.focus({ preventScroll: true });
  });

  // Owner identity
  try {
    const { owner_name } = await getConfig();
    const first = owner_name.split(/\s+/)[0];
    document.title = `${owner_name} — Avatar`;
    (document.getElementById("brandSub") as HTMLElement).textContent =
      `${owner_name} · digital twin`;
    (document.getElementById("introTitle") as HTMLElement).innerHTML =
      `I'm ${escapeHtml(first)}'s <em>digital twin</em>.<br>Ask me anything — and the real ${escapeHtml(first)} might just chime in.`;
    (document.getElementById("introText") as HTMLElement).textContent =
      `I know ${first}'s background and work, and I can put you in touch with ${first} directly.`;
    composerInput.placeholder = `Message ${first}'s twin…  (type “Q2” for an instant answer)`;
    const chips = suggestRow.querySelectorAll("button");
    chips[chips.length - 1].textContent = `Can I talk to the real ${first}?`;
    const noticeText = `Real replies from ${first} within 24h if needed — feel free to check back`;
    (document.getElementById("replyNoticeText") as HTMLElement).textContent = noticeText;
    (document.getElementById("replyNotice") as HTMLElement).title = noticeText;
  } catch {
    /* offline config — leave generic copy */
  }

  // Conversation identity + restore
  const existing = keepChat.checked ? getCookie(CID_COOKIE) : null;
  if (existing) {
    conversationId = existing;
    try {
      const thread = await getConversation(conversationId);
      if (thread.messages.length > 0) renderHistory(thread.messages);
    } catch {
      /* fetch failed — start fresh below */
    }
  }
  if (!conversationId) newConversation();

  // ?q=N deep link: submit QN immediately, then strip the param.
  const params = new URLSearchParams(location.search);
  const q = params.get("q");
  if (q && /^\d{1,2}$/.test(q)) {
    history.replaceState(null, "", location.pathname);
    void send(`Q${q}`, { autoDeepLink: true });
  }

  schedulePoll();
  composerInput.focus({ preventScroll: true });
  maybeStartTour();
}

function newConversation(): void {
  conversationId = crypto.randomUUID();
  lastMessageId = 0;
  if (keepChat.checked) setCookie(CID_COOKIE, conversationId);
}

function resetChat(): void {
  messagesEl.innerHTML = "";
  intro.hidden = false;
  newConversation();
  composerInput.focus({ preventScroll: true });
}

function renderHistory(messages: Message[]): void {
  intro.hidden = true;
  lastDay = null;
  for (const message of messages) appendMessage(message);
  scrollToLatest();
}

/** Insert a "Aug 7" divider whenever a message lands on a new calendar day. */
function maybeInsertDaySep(iso: string | Date): void {
  const key = dayKey(iso);
  if (key === lastDay) return;
  lastDay = key;
  const sep = document.createElement("div");
  sep.className = "day-sep";
  sep.innerHTML = `<span>${dayLabel(iso)}</span>`;
  messagesEl.appendChild(sep);
}

function appendMessage(message: Message): void {
  maybeInsertDaySep(message.created_at);
  lastMessageId = Math.max(lastMessageId, message.id);
  const el = createMessageEl({
    role: message.role,
    content: message.content,
    time: formatTime(message.created_at),
    initials: initialsFor(nameField.value || message.conversation_name),
    instantTag: instantTagFor(message),
  });
  messagesEl.appendChild(el);
}

function instantTagFor(message: Message): string | undefined {
  const instant = message.tool_calls?.find((t) => t.tool === "instant_faq");
  return instant && "faq_number" in instant
    ? `instant · Q${(instant as { faq_number: number }).faq_number}`
    : undefined;
}

async function send(raw: string, options: { autoDeepLink?: boolean } = {}): Promise<void> {
  const text = raw.trim();
  if (!text || sending) return;

  // Mandatory name/initials — every message needs one so the inbox is never
  // just "Visitor". The one exemption is the ?q=N auto-submit on page load,
  // which fires before the visitor could have typed anything.
  if (!nameField.value.trim() && !options.autoDeepLink) {
    nameField.focus();
    nameFieldWrap.classList.remove("is-error");
    void nameFieldWrap.offsetWidth; // restart the shake animation on repeat attempts
    nameFieldWrap.classList.add("is-error");
    addSysNote("Please add your name or initials above before we can chat.");
    return;
  }

  sending = true;
  sendBtn.disabled = true;
  intro.hidden = true;
  composerInput.value = "";
  autoGrow();
  lastActivity = Date.now();
  schedulePoll();

  // Attention toggle: consume it for this message, reset the button at once.
  const attention = attnBtn.classList.contains("is-on");
  attnBtn.classList.remove("is-on");
  attnBtn.setAttribute("aria-pressed", "false");

  maybeInsertDaySep(new Date());
  const visitorEl = createMessageEl({
    role: "visitor",
    content: text,
    time: formatTime(new Date()),
    initials: initialsFor(nameField.value),
  });
  messagesEl.appendChild(visitorEl);
  scrollToLatest();
  composerInput.focus({ preventScroll: true });

  let avatarEl: HTMLElement | undefined;
  let bubble: HTMLElement | undefined;
  let body: HTMLElement | undefined;
  let streamed = "";
  const toolEls = new Map<string, HTMLElement>();

  const ensureAvatarEl = (instantTag?: string) => {
    if (avatarEl) return;
    avatarEl = createMessageEl({
      role: "avatar",
      content: "",
      time: formatTime(new Date()),
      instantTag,
    });
    body = avatarEl.querySelector(".msg-body") as HTMLElement;
    bubble = avatarEl.querySelector(".bubble") as HTMLElement;
    messagesEl.appendChild(avatarEl);
  };

  typing.hidden = false;
  scrollToLatest();

  try {
    for await (const { event, data } of streamChat({
      conversation_id: conversationId,
      message: text,
      visitor_name: nameField.value.trim() || undefined,
      attention: attention || undefined,
      auto_deep_link: options.autoDeepLink || undefined,
    })) {
      switch (event) {
        case "visitor_message": {
          lastMessageId = Math.max(lastMessageId, data.id as number);
          const vb = visitorEl.querySelector(".bubble") as HTMLElement;
          vb.innerHTML = renderMarkdown(data.content as string);
          break;
        }
        case "meta":
          if (data.mode === "instant")
            ensureAvatarEl(`instant · Q${data.faq_number}`);
          break;
        case "tool_call": {
          ensureAvatarEl();
          typing.hidden = true;
          const toolEl = createToolStatusEl(data.tool as string);
          toolEls.set(data.tool as string, toolEl);
          body!.insertBefore(toolEl, bubble!);
          scrollToLatest();
          break;
        }
        case "tool_result": {
          const toolEl = toolEls.get(data.tool as string);
          if (toolEl) markToolStatusDone(toolEl, data.tool as string);
          break;
        }
        case "token":
          ensureAvatarEl();
          typing.hidden = true;
          streamed += data.text as string;
          bubble!.innerHTML = renderMarkdown(streamed);
          scrollToLatest();
          break;
        case "done":
          lastMessageId = Math.max(lastMessageId, data.id as number);
          break;
        case "error":
          ensureAvatarEl();
          typing.hidden = true;
          bubble!.innerHTML = renderMarkdown(
            streamed ||
              "Sorry — something went wrong on my side. Please try that again.",
          );
          break;
      }
    }
  } catch (error) {
    typing.hidden = true;
    if (!streamed && avatarEl) avatarEl.remove();
    if (error instanceof RateLimitError) {
      addSysNote("You're sending messages too quickly — give it a few seconds and try again.");
    } else if (error instanceof NameRequiredError) {
      visitorEl.remove();
      addSysNote("Please add your name or initials above before we can chat.");
    } else if (error instanceof BlockedError) {
      visitorEl.remove();
      addSysNote("You're no longer able to send messages in this conversation.");
    } else {
      addSysNote("Connection hiccup — that message didn't go through. Please try again.");
    }
  } finally {
    typing.hidden = true;
    sending = false;
    sendBtn.disabled = false;
    lastActivity = Date.now();
    scrollToLatest();
    composerInput.focus({ preventScroll: true });
  }
}

function addSysNote(text: string): void {
  const note = document.createElement("div");
  note.className = "sys-note";
  note.textContent = text;
  messagesEl.appendChild(note);
  scrollToLatest();
}

/* ---- Polling for the human's async messages ---- */

function schedulePoll(): void {
  if (pollTimer) clearTimeout(pollTimer);
  const idleMs = Date.now() - lastActivity;
  const interval = idleMs > 5 * 60 * 1000 ? 60_000 : 10_000;
  pollTimer = window.setTimeout(() => void poll(), interval);
}

async function poll(): Promise<void> {
  if (!sending && conversationId) {
    try {
      const { messages } = await getConversation(conversationId, lastMessageId);
      for (const message of messages) {
        appendMessage(message);
        lastActivity = Date.now();
      }
      if (messages.length > 0) scrollToLatest();
    } catch {
      /* transient network failure — next poll retries */
    }
  }
  schedulePoll();
}

/* ---- Small helpers ---- */

function scrollToLatest(): void {
  convo.scrollTop = convo.scrollHeight;
}

function autoGrow(): void {
  composerInput.style.height = "auto";
  composerInput.style.height = `${Math.min(composerInput.scrollHeight, 180)}px`;
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
