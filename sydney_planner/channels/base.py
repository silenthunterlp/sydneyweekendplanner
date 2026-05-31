from abc import ABC, abstractmethod

from sydney_planner.agent.core import PlannerAgent


class ChannelAdapter(ABC):
    def __init__(self, agent: PlannerAgent) -> None:
        self.agent = agent

    @staticmethod
    def normalize_user_id(raw_id: str, channel: str) -> str:
        """Prefix channel to avoid cross-channel ID collisions."""
        return f"{channel}:{raw_id}"
