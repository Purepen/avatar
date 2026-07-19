/** Admin dashboard.
 *
 * - Password gate -> signed httpOnly session cookie guards every /admin/* API.
 * - Inbox: most recent first, unread dot / amber needs-you states, search and
 *   filter chips; ArrowUp/ArrowDown move the selection.
 * - Opening a thread marks it read + clears needs_attention (single backend
 *   round-trip) and, on mobile, switches the master/detail view.
 * - Enter sends, Shift+Enter newline. The Avatar never reacts to these posts.
 */

import {
  adminChangePassword,
  adminInbox,
  adminLogin,
  adminOpenThread,
  adminPostMessage,
  adminResetConfirm,
  adminResetRequest,
  adminResolve,
  adminSession,
  getConfig,
  getConversation,
  type InboxEntry,
  type Message,
} from "../lib/api";
import {
  createMessageEl,
  createToolStatusEl,
  formatTime,
  initialsFor,
  markToolStatusDone,
} from "../lib/messages";
import { initTheme } from "../lib/theme";

const loginGate = document.getElementById("loginGate") as HTMLElement;
const loginForm = document.getElementById("loginForm") as HTMLFormElement;
const passwordInput = document.getElementById("passwordInput") as HTMLInputElement;
const loginError = document.getElementById("loginError") as HTMLElement;
const dashboard = document.getElementById("dashboard") as HTMLElement;
const workspace = document.getElementById("workspace") as HTMLElement;
const convoList = document.getElementById("convoList") as HTMLElement;
const countBadge = document.getElementById("countBadge") as HTMLElement;
const searchInput = document.getElementById("searchInput") as HTMLInputElement;
const filterRow = document.getElementById("filterRow") as HTMLElement;
const threadHead = document.getElementById("threadHead") as HTMLElement;
const threadInner = document.getElementById("threadInner") as HTMLElement;
const threadEl = document.getElementById("thread") as HTMLElement;
const emptyState = document.getElementById("emptyState") as HTMLElement;
const composerDock = document.getElementById("composerDock") as HTMLElement;
const composerInput = document.getElementById("composerInput") as HTMLTextAreaElement;
const sendBtn = document.getElementById("sendBtn") as HTMLButtonElement;
const resolveBtn = document.getElementById("resolveBtn") as HTMLButtonElement;
const attnFlag = document.getElementById("attnFlag") as HTMLElement;
const backBtn = document.getElementById("backBtn") as HTMLButtonElement;

let inbox: InboxEntry[] = [];
let activeId: string | null = null;
let activeHadAttention = false;
let lastThreadMessageId = 0;
let threadMessages: Message[] = [];
let filter: "all" | "attention" | "unread" = "all";
let threadTimer: number | undefined;

init();

async function init(): Promise<void> {
  initTheme();
  try {
    const { owner_name } = await getConfig();
    document.title = `${owner_name} — Avatar Admin`;
    const posting = document.getElementById("postingAsName");
    if (posting) posting.textContent = owner_name;
  } catch {
    /* keep generic copy */
  }

  const session = await adminSession();
  if (session.ok) {
    showDashboard();
  } else {
    loginGate.hidden = false;
    passwordInput.focus();
  }

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const response = await adminLogin(passwordInput.value);
    if (response.ok) {
      loginError.hidden = true;
      showDashboard();
    } else {
      loginError.hidden = false;
      passwordInput.select();
    }
  });

  wirePasswordFlows();
}

function wirePasswordFlows(): void {
  const resetForm = document.getElementById("resetForm") as HTMLFormElement;
  const resetError = document.getElementById("resetError") as HTMLElement;

  // Forgot password: request a Pushover code, swap to the reset card.
  (document.getElementById("forgotBtn") as HTMLButtonElement).addEventListener(
    "click",
    async () => {
      const response = await adminResetRequest();
      loginForm.hidden = true;
      resetForm.hidden = false;
      if (!response.ok) {
        const detail = (await response.json().catch(() => null))?.detail;
        resetError.textContent =
          detail ?? "Could not send a reset code — try again later.";
        resetError.hidden = false;
      } else {
        resetError.hidden = true;
        (document.getElementById("resetCode") as HTMLInputElement).focus();
      }
    },
  );

  (document.getElementById("resetBack") as HTMLButtonElement).addEventListener(
    "click",
    () => {
      resetForm.hidden = true;
      loginForm.hidden = false;
      passwordInput.focus();
    },
  );

  resetForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const code = (document.getElementById("resetCode") as HTMLInputElement).value.trim();
    const newPassword = (
      document.getElementById("resetNewPassword") as HTMLInputElement
    ).value;
    const response = await adminResetConfirm(code, newPassword);
    if (response.ok) {
      resetForm.hidden = true;
      showDashboard();
    } else {
      const detail = (await response.json().catch(() => null))?.detail;
      resetError.textContent = detail ?? "Reset failed — check the code.";
      resetError.hidden = false;
    }
  });

  // Change password (from inside the dashboard).
  const modal = document.getElementById("pwModal") as HTMLElement;
  const pwForm = document.getElementById("pwForm") as HTMLFormElement;
  const pwError = document.getElementById("pwError") as HTMLElement;
  const pwSuccess = document.getElementById("pwSuccess") as HTMLElement;

  (document.getElementById("changePwBtn") as HTMLButtonElement).addEventListener(
    "click",
    () => {
      pwForm.reset();
      pwError.hidden = true;
      pwSuccess.hidden = true;
      modal.hidden = false;
      (document.getElementById("pwCurrent") as HTMLInputElement).focus();
    },
  );
  (document.getElementById("pwCancel") as HTMLButtonElement).addEventListener(
    "click",
    () => (modal.hidden = true),
  );
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.hidden = true;
  });

  pwForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const current = (document.getElementById("pwCurrent") as HTMLInputElement).value;
    const next = (document.getElementById("pwNew") as HTMLInputElement).value;
    const confirm = (document.getElementById("pwConfirm") as HTMLInputElement).value;
    if (next !== confirm) {
      pwError.textContent = "New passwords don't match.";
      pwError.hidden = false;
      return;
    }
    const response = await adminChangePassword(current, next);
    if (response.ok) {
      pwError.hidden = true;
      pwSuccess.hidden = false;
      setTimeout(() => (modal.hidden = true), 1200);
    } else {
      const detail = (await response.json().catch(() => null))?.detail;
      pwError.textContent = detail ?? "Password change failed.";
      pwError.hidden = false;
    }
  });
}

function showDashboard(): void {
  loginGate.hidden = true;
  dashboard.hidden = false;
  wireDashboard();
  void refreshInbox();
  window.setInterval(() => void refreshInbox(), 30_000);
}

function wireDashboard(): void {
  searchInput.addEventListener("input", () => {
    renderInbox();
    // Live-highlight the searched term inside the open thread too.
    if (activeId && threadMessages.length > 0) {
      renderThread(threadMessages);
    }
  });
  filterRow.addEventListener("click", (e) => {
    const chip = (e.target as HTMLElement).closest(".filter-chip");
    if (!chip) return;
    filter = chip.getAttribute("data-filter") as typeof filter;
    filterRow.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("is-on"));
    chip.classList.add("is-on");
    renderInbox();
  });

  composerInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  });
  composerInput.addEventListener("input", autoGrow);
  sendBtn.addEventListener("click", () => void sendMessage());
  resolveBtn.addEventListener("click", () => void resolveActive());
  backBtn.addEventListener("click", () => workspace.classList.remove("show-thread"));

  // Arrow keys move between conversations (unless typing multi-line text).
  document.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
    if (document.activeElement === composerInput && composerInput.value !== "") return;
    if (document.activeElement === searchInput || document.activeElement === passwordInput) return;
    e.preventDefault();
    moveSelection(e.key === "ArrowDown" ? 1 : -1);
  });
}

/* ---- Inbox ---- */

async function refreshInbox(): Promise<void> {
  try {
    inbox = await adminInbox();
  } catch {
    return; // transient failure; next refresh retries
  }
  countBadge.textContent = String(inbox.length);
  updateFilterCounts();
  renderInbox();
}

function updateFilterCounts(): void {
  const attention = inbox.filter((e) => e.needs_attention).length;
  const unread = inbox.filter((e) => e.unread_count > 0).length;
  const chips = filterRow.querySelectorAll(".filter-chip");
  chips[1].innerHTML = `<span class="dot-y"></span>Needs you${attention ? ` · ${attention}` : ""}`;
  chips[2].textContent = `Unread${unread ? ` · ${unread}` : ""}`;
}

function visibleEntries(): InboxEntry[] {
  const term = searchInput.value.trim().toLowerCase();
  return inbox.filter((entry) => {
    if (filter === "attention" && !entry.needs_attention) return false;
    if (filter === "unread" && entry.unread_count === 0) return false;
    if (
      term &&
      !(entry.conversation_name ?? "").toLowerCase().includes(term) &&
      !entry.search_blob.includes(term)
    )
      return false;
    return true;
  });
}

function renderInbox(): void {
  convoList.innerHTML = "";
  for (const entry of visibleEntries()) {
    const item = document.createElement("div");
    const classes = ["convo-item"];
    if (entry.conversation_id === activeId) classes.push("is-active");
    if (entry.unread_count > 0) classes.push("is-unread");
    if (entry.needs_attention) classes.push("is-attention");
    item.className = classes.join(" ");

    const name = entry.conversation_name || "Visitor";
    const side = entry.needs_attention
      ? `<span class="badge badge--attention"><svg class="icon" style="width:11px;height:11px"><use href="/icons.svg#i-spark"/></svg> Needs you</span>`
      : entry.unread_count > 0
        ? `<span class="badge badge--dot"></span>`
        : `<svg class="icon icon--sm" style="color:var(--positive)"><use href="/icons.svg#i-check2"/></svg>`;

    item.innerHTML = `
      <span class="avatar-initials">${escapeHtml(initialsFor(name))}</span>
      <div class="convo-main">
        <div class="convo-top"><span class="convo-name">${escapeHtml(name)}</span></div>
        <div class="convo-preview">${highlightText(stripMarkdown(entry.preview), searchInput.value.trim())}</div>
      </div>
      <div class="convo-side">
        <span class="msg-time">${formatTime(entry.last_message_at)}</span>
        ${side}
      </div>`;
    item.addEventListener("click", () => void openThread(entry.conversation_id));
    convoList.appendChild(item);
  }
}

function moveSelection(delta: number): void {
  const entries = visibleEntries();
  if (entries.length === 0) return;
  const index = entries.findIndex((e) => e.conversation_id === activeId);
  const next = entries[Math.min(entries.length - 1, Math.max(0, index + delta))];
  if (next && next.conversation_id !== activeId) void openThread(next.conversation_id);
}

/* ---- Thread ---- */

async function openThread(conversationId: string): Promise<void> {
  const entry = inbox.find((e) => e.conversation_id === conversationId);
  activeHadAttention = entry?.needs_attention ?? false;
  activeId = conversationId;

  const thread = await adminOpenThread(conversationId);
  threadMessages = thread.messages;

  // Opening cleared unread + attention server-side; mirror it locally.
  if (entry) {
    entry.unread_count = 0;
    entry.needs_attention = false;
  }
  updateFilterCounts();
  renderInbox();

  const name = thread.conversation_name || "Visitor";
  (document.getElementById("threadInitials") as HTMLElement).textContent = initialsFor(name);
  (document.getElementById("threadName") as HTMLElement).textContent = name;
  const first = thread.messages[0];
  (document.getElementById("threadSub") as HTMLElement).textContent =
    `conv_${conversationId.slice(0, 6)} · started ${first ? formatTime(first.created_at) : "–"} · ${thread.messages.length} messages`;
  attnFlag.hidden = !activeHadAttention;

  threadHead.hidden = false;
  composerDock.hidden = false;
  emptyState.remove();
  renderThread(thread.messages);
  workspace.classList.add("show-thread");
  composerInput.focus({ preventScroll: true });

  if (threadTimer) clearInterval(threadTimer);
  threadTimer = window.setInterval(() => void pollThread(), 10_000);
}

function renderThread(messages: Message[]): void {
  threadInner.innerHTML = "";
  if (messages.length > 0) {
    const sep = document.createElement("div");
    sep.className = "day-sep";
    sep.innerHTML = `<span>${new Date(messages[0].created_at).toLocaleDateString([], { month: "short", day: "numeric" })}</span>`;
    threadInner.appendChild(sep);
  }
  lastThreadMessageId = 0;
  for (const message of messages) appendThreadMessage(message);
  // Highlight the active search term across the whole history and jump to
  // the first hit, so the admin sees exactly where the match lives.
  const term = searchInput.value.trim();
  if (term) {
    highlightInElement(threadInner, term);
    const hit = threadInner.querySelector("mark.search-hit");
    if (hit) {
      hit.scrollIntoView({ block: "center" });
      return;
    }
  }
  scrollThread();
}

function appendThreadMessage(message: Message): HTMLElement {
  lastThreadMessageId = Math.max(lastThreadMessageId, message.id);
  const el = createMessageEl({
    role: message.role,
    content: message.content,
    time: formatTime(message.created_at),
    initials: initialsFor(message.conversation_name || inboxNameFor(message.conversation_id)),
    humanTagText: "You · sent to visitor",
    instantTag: instantTagFor(message),
  });
  // Show tool usage as done-state status lines above the avatar's bubble.
  if (message.role === "avatar" && message.tool_calls) {
    const body = el.querySelector(".msg-body") as HTMLElement;
    const bubble = el.querySelector(".bubble") as HTMLElement;
    for (const call of message.tool_calls) {
      if (call.tool === "instant_faq") continue;
      const status = createToolStatusEl(call.tool);
      markToolStatusDone(status, call.tool);
      body.insertBefore(status, bubble);
    }
  }
  threadInner.appendChild(el);
  return el;
}

function instantTagFor(message: Message): string | undefined {
  const instant = message.tool_calls?.find((t) => t.tool === "instant_faq");
  return instant && "faq_number" in instant
    ? `instant · Q${(instant as { faq_number: number }).faq_number}`
    : undefined;
}

function inboxNameFor(conversationId: string): string | null {
  return inbox.find((e) => e.conversation_id === conversationId)?.conversation_name ?? null;
}

async function pollThread(): Promise<void> {
  if (!activeId) return;
  try {
    const { messages } = await getConversation(activeId, lastThreadMessageId);
    if (messages.length > 0) {
      const term = searchInput.value.trim();
      for (const message of messages) {
        threadMessages.push(message);
        const el = appendThreadMessage(message);
        if (term) highlightInElement(el, term);
      }
      scrollThread();
    }
  } catch {
    /* transient */
  }
}

async function sendMessage(): Promise<void> {
  const content = composerInput.value.trim();
  if (!content || !activeId) return;
  composerInput.value = "";
  autoGrow();
  const message = await adminPostMessage(activeId, content);
  threadMessages.push(message);
  appendThreadMessage(message);
  scrollThread();
  composerInput.focus({ preventScroll: true });
}

async function resolveActive(): Promise<void> {
  if (!activeId) return;
  await adminResolve(activeId);
  attnFlag.hidden = true;
  const entry = inbox.find((e) => e.conversation_id === activeId);
  if (entry) entry.needs_attention = false;
  updateFilterCounts();
  renderInbox();
}

/* ---- Helpers ---- */

function scrollThread(): void {
  threadEl.scrollTop = threadEl.scrollHeight;
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

function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[`#>]/g, "");
}

/** Escape text to HTML, wrapping case-insensitive matches of term in a
 *  <mark class="search-hit"> so the admin sees where the search matched. */
function highlightText(text: string, term: string): string {
  if (!term) return escapeHtml(text);
  const lower = text.toLowerCase();
  const needle = term.toLowerCase();
  const parts: string[] = [];
  let pos = 0;
  let i = lower.indexOf(needle);
  while (i !== -1) {
    parts.push(escapeHtml(text.slice(pos, i)));
    parts.push(`<mark class="search-hit">${escapeHtml(text.slice(i, i + term.length))}</mark>`);
    pos = i + term.length;
    i = lower.indexOf(needle, pos);
  }
  parts.push(escapeHtml(text.slice(pos)));
  return parts.join("");
}

/** Wrap term matches in <mark> across all rendered text inside root
 *  (walks text nodes, so rendered markdown formatting is preserved). */
function highlightInElement(root: HTMLElement, term: string): void {
  const needle = term.toLowerCase();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const textNodes: Text[] = [];
  let node;
  while ((node = walker.nextNode())) textNodes.push(node as Text);
  for (const textNode of textNodes) {
    const text = textNode.data;
    const lower = text.toLowerCase();
    let i = lower.indexOf(needle);
    if (i === -1) continue;
    const frag = document.createDocumentFragment();
    let pos = 0;
    while (i !== -1) {
      frag.appendChild(document.createTextNode(text.slice(pos, i)));
      const mark = document.createElement("mark");
      mark.className = "search-hit";
      mark.textContent = text.slice(i, i + term.length);
      frag.appendChild(mark);
      pos = i + term.length;
      i = lower.indexOf(needle, pos);
    }
    frag.appendChild(document.createTextNode(text.slice(pos)));
    textNode.parentNode?.replaceChild(frag, textNode);
  }
}
