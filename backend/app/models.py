"""Pydantic request/response models."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str = Field(min_length=32, max_length=64)
    message: str = Field(min_length=1)
    visitor_name: str | None = Field(default=None, max_length=60)
    # The composer's attention toggle: this message also pings the human
    # directly (push notification), independent of what the model decides.
    attention: bool = False
    # Set only by the ?q=N auto-submit on page load — the one exemption from
    # the mandatory-name rule, since the visitor hasn't typed anything yet.
    auto_deep_link: bool = False


class LoginRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ResetConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=128)


class AdminMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)


class Message(BaseModel):
    id: int
    conversation_id: str
    conversation_name: str | None = None
    role: str
    content: str
    tool_calls: list | None = None
    needs_attention: bool = False
    read: bool = False
    created_at: str


class ConversationResponse(BaseModel):
    conversation_id: str
    conversation_name: str | None = None
    messages: list[Message]
    avatar_muted: bool = False
    visitor_blocked: bool = False


class InboxEntry(BaseModel):
    conversation_id: str
    conversation_name: str | None = None
    last_message_at: str
    last_role: str
    preview: str
    message_count: int
    unread_count: int
    needs_attention: bool
    search_blob: str = ""
    avatar_muted: bool = False
    visitor_blocked: bool = False


class ConversationStateResponse(BaseModel):
    avatar_muted: bool
    visitor_blocked: bool


class ConfigResponse(BaseModel):
    owner_name: str
