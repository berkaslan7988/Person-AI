"""Person AI - ChatSession and Message dataclasses."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Message:
    """A single message in a chat."""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Build a Message from a stored dict, tolerating missing/extra keys."""
        msg = cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
        )
        if data.get("timestamp"):
            msg.timestamp = data["timestamp"]
        return msg

    def to_openai_format(self) -> dict:
        """Convert to OpenAI-compatible message dict."""
        role = "assistant" if self.role in ("assistant", "model") else self.role
        return {"role": role, "content": self.content}


@dataclass
class ChatSession:
    """Represents a conversation with a character."""
    id: Optional[int] = None
    character_id: Optional[int] = None
    character_name: str = ""
    title: Optional[str] = None
    messages: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add(self, message: Message):
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

    def clear(self):
        self.messages.clear()
        self.updated_at = datetime.now().isoformat()

    def recent_messages(self, count: int) -> list[Message]:
        """Return the last `count` messages."""
        return self.messages[-count:] if count > 0 else self.messages[:]

    @property
    def message_count(self) -> int:
        return len(self.messages)
