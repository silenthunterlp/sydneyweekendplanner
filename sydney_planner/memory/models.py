from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    channel: Mapped[str] = mapped_column(String)  # "web" | "whatsapp" | "telegram"

    home_suburb: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    budget_per_day_aud: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # e.g. ["outdoor", "arts", "food", "sports", "family", "nightlife", "markets", "music"]
    interests: Mapped[list] = mapped_column(JSON, default=list)

    # "public_transport" | "driving" | "walking" | "cycling"
    preferred_transport: Mapped[str] = mapped_column(String, default="public_transport")

    accessibility_needs: Mapped[bool] = mapped_column(Boolean, default=False)

    # "solo" | "couple" | "family_with_kids" | "friends_group"
    group_type: Mapped[str] = mapped_column(String, default="solo")
    children_ages: Mapped[list] = mapped_column(JSON, default=list)

    avoids_rain: Mapped[bool] = mapped_column(Boolean, default=True)
    max_travel_time_minutes: Mapped[int] = mapped_column(Integer, default=60)
    prefers_early_start: Mapped[bool] = mapped_column(Boolean, default=False)

    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "channel": self.channel,
            "home_suburb": self.home_suburb,
            "budget_per_day_aud": self.budget_per_day_aud,
            "interests": self.interests or [],
            "preferred_transport": self.preferred_transport,
            "accessibility_needs": self.accessibility_needs,
            "group_type": self.group_type,
            "children_ages": self.children_ages or [],
            "avoids_rain": self.avoids_rain,
            "max_travel_time_minutes": self.max_travel_time_minutes,
            "prefers_early_start": self.prefers_early_start,
            "onboarding_complete": self.onboarding_complete,
        }


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    weekend_reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
