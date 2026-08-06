/** Shared message-bubble rendering for the visitor and admin pages.
 *
 * Role identity (design system):
 *   visitor — right-aligned, sky initials token
 *   avatar  — left, robot image, green ring, tool-status above the bubble
 *   human   — left, owner photo, indigo ring + spark badge, name-free tag
 */

import { renderMarkdown } from "./markdown";

export type Role = "visitor" | "avatar" | "human";

export function initialsFor(name: string | null | undefined): string {
  const trimmed = (name ?? "").trim();
  if (!trimmed) return "V";
  const parts = trimmed.split(/\s+/).filter(Boolean);
  const letters =
    parts.length >= 2
      ? parts[0][0] + parts[parts.length - 1][0]
      : trimmed.replace(/[^a-zA-Z0-9]/g, "").slice(0, 2) || "V";
  return letters.toUpperCase();
}

export function formatTime(iso: string | Date): string {
  const date = typeof iso === "string" ? new Date(iso) : iso;
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** "Aug 7, 5:23 PM" — used where a bare time is ambiguous (e.g. the inbox
 *  row, which may show the last message from days ago). */
export function formatDateTime(iso: string | Date): string {
  const date = typeof iso === "string" ? new Date(iso) : iso;
  const datePart = date.toLocaleDateString([], { month: "short", day: "numeric" });
  return `${datePart}, ${formatTime(date)}`;
}

/** Calendar-day key for grouping messages under day separators. */
export function dayKey(iso: string | Date): string {
  const date = typeof iso === "string" ? new Date(iso) : iso;
  return date.toDateString();
}

export function dayLabel(iso: string | Date): string {
  const date = typeof iso === "string" ? new Date(iso) : iso;
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export interface MessageOptions {
  role: Role;
  content: string;
  time?: string;
  initials?: string;
  instantTag?: string; // e.g. "instant · Q2"
  humanTagText?: string; // visitor page: "The human · live"; admin: "You · sent to visitor"
}

export function createMessageEl(options: MessageOptions): HTMLElement {
  const el = document.createElement("div");
  el.className = `msg msg--${options.role}`;

  const avatar =
    options.role === "visitor"
      ? `<span class="avatar-initials">${escapeHtml(options.initials ?? "V")}</span>`
      : options.role === "avatar"
        ? `<div class="avatar avatar-twin" style="background-image:url('/avatar-robot-round.png')"></div>`
        : `<div class="avatar avatar-human" style="background-image:url('/avatar-human.png')">
             <span class="spark-badge"><svg class="icon"><use href="/icons.svg#i-spark"/></svg></span>
           </div>`;

  const metaBits: string[] = [];
  if (options.role === "avatar") metaBits.push(`<span class="msg-name">Avatar</span>`);
  if (options.role === "human")
    metaBits.push(
      `<span class="human-tag"><svg class="icon"><use href="/icons.svg#i-live"/></svg> ${escapeHtml(
        options.humanTagText ?? "The human · live",
      )}</span>`,
    );
  if (options.instantTag)
    metaBits.push(`<span class="instant-tag">${escapeHtml(options.instantTag)}</span>`);
  if (options.time) metaBits.push(`<span class="msg-time">${escapeHtml(options.time)}</span>`);

  el.innerHTML = `
    ${avatar}
    <div class="msg-body">
      <div class="msg-meta">${metaBits.join("")}</div>
      <div class="bubble">${renderMarkdown(options.content)}</div>
    </div>`;
  return el;
}

/** A small mono tool-status row, inserted above the avatar bubble. */
export function createToolStatusEl(tool: string): HTMLElement {
  const el = document.createElement("div");
  el.className = "tool-status";
  el.innerHTML = `<svg class="icon"><use href="/icons.svg#i-tool"/></svg> Calling ${escapeHtml(tool)}…`;
  return el;
}

export function markToolStatusDone(el: HTMLElement, tool: string): void {
  el.className = "tool-status is-done";
  el.innerHTML = `<svg class="icon"><use href="/icons.svg#i-check"/></svg> ${escapeHtml(tool)} · returned`;
}

export function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
