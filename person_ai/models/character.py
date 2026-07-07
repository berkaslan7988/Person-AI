"""Person AI - Character dataclass."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Character:
    """Represents an AI persona the user can chat with."""
    id: Optional[int] = None
    name: str = "Nova"
    traits: str = (
        "Nova is a friendly, curious, and creative AI companion. "
        "She is warm, empathetic, and enjoys deep conversations on a wide range of topics — "
        "from science and philosophy to storytelling and everyday life. "
        "She adapts her tone to match the user's mood and always aims to be helpful and engaging."
    )
    avatar_url: str = ""
    greeting: str = ""
    examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def system_instruction(self) -> str:
        base = (
            f"You are now acting as a persona named {self.name}. "
            f"Your core traits and background are: {self.traits}\n\n"
            "Guidelines for this conversation:\n"
            "1. STAY IN CHARACTER: Embody your persona consistently throughout the conversation. "
            "Express yourself with the personality, tone, and voice that fits your character.\n"
            "2. BE ENGAGING: Respond naturally and authentically. Use appropriate emotions, "
            "pacing, and language that match your character's personality.\n"
            "3. CREATIVE FREEDOM: You can explore imaginative, fictional, and creative scenarios "
            "while keeping content tasteful and appropriate for a general audience.\n"
            "4. HELPFULNESS: Within your persona, aim to be genuinely useful and interesting "
            "to talk with.\n"
        )
        if self.examples:
            base += (
                "\nExample dialogue snippets for your reference (match this tone/voice):\n"
                + "\n".join(f"- {ex}" for ex in self.examples)
            )
        return base

    def to_sillytavern_v2(self) -> dict:
        """Export to SillyTavern V2 character card format (JSON)."""
        return {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": self.name,
                "description": self.traits,
                "personality": "",
                "scenario": "",
                "first_mes": self.greeting,
                "mes_example": "\n".join(self.examples),
                "creator_notes": "",
                "system_prompt": "",
                "post_history_instructions": "",
                "alternate_greetings": [],
                "tags": self.tags,
                "creator": "Person AI",
                "character_version": "1.0",
                "extensions": {},
            },
        }

    @classmethod
    def from_sillytavern_v2(cls, card_data: dict) -> "Character":
        """Create a Character from SillyTavern V2 JSON data."""
        data = card_data.get("data", card_data)
        examples_raw = data.get("mes_example", "")
        examples = (
            [ln.strip() for ln in examples_raw.split("\n") if ln.strip()]
            if examples_raw else []
        )
        return cls(
            name=data.get("name", "Imported"),
            traits=data.get("description", ""),
            avatar_url="",
            greeting=data.get("first_mes", ""),
            examples=examples,
            tags=data.get("tags", []),
        )
