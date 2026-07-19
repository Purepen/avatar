/** Typed wrappers for the backend API. */

export interface Message {
  id: number;
  conversation_id: string;
  conversation_name: string | null;
  role: "visitor" | "avatar" | "human";
  content: string;
  tool_calls: { tool: string }[] | null;
  needs_attention: boolean;
  read: boolean;
  created_at: string;
}

export interface Conversation {
  conversation_id: string;
  conversation_name: string | null;
  messages: Message[];
}

export interface InboxEntry {
  conversation_id: string;
  conversation_name: string | null;
  last_message_at: string;
  last_role: string;
  preview: string;
  message_count: number;
  unread_count: number;
  needs_attention: boolean;
  search_blob: string;
}

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status);
  return response.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number) {
    super(`API error ${status}`);
  }
}

export const getConfig = () =>
  fetch("/api/config").then((r) => json<{ owner_name: string }>(r));

export const getConversation = (conversationId: string, afterId?: number) =>
  fetch(
    `/api/conversation/${conversationId}` +
      (afterId !== undefined ? `?after_id=${afterId}` : ""),
  ).then((r) => json<Conversation>(r));

export const adminLogin = (password: string) =>
  fetch("/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });

export const adminSession = () => fetch("/admin/session");

export const adminInbox = () =>
  fetch("/admin/conversations").then((r) => json<InboxEntry[]>(r));

export const adminOpenThread = (conversationId: string) =>
  fetch(`/admin/conversations/${conversationId}`).then((r) =>
    json<Conversation>(r),
  );

export const adminPostMessage = (conversationId: string, content: string) =>
  fetch(`/admin/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  }).then((r) => json<Message>(r));

export const adminResolve = (conversationId: string) =>
  fetch(`/admin/conversations/${conversationId}/resolve`, { method: "POST" });

export const adminChangePassword = (currentPassword: string, newPassword: string) =>
  fetch("/admin/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

export const adminResetRequest = () =>
  fetch("/admin/reset/request", { method: "POST" });

export const adminResetConfirm = (code: string, newPassword: string) =>
  fetch("/admin/reset/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, new_password: newPassword }),
  });
