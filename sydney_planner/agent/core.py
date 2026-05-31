import json
from typing import Any

import anthropic

from sydney_planner.agent.prompts import build_system_prompt
from sydney_planner.agent.tool_handlers import ToolHandlers
from sydney_planner.agent.tools import TOOLS
from sydney_planner.config import get_settings
from sydney_planner.memory.repository import UserPreferencesRepository
from sydney_planner.utils.date_helpers import get_upcoming_weekend


def _extract_text(content: list) -> str:
    parts = [block.text for block in content if hasattr(block, "text")]
    return "\n".join(parts).strip()


class PlannerAgent:
    def __init__(self, repo: UserPreferencesRepository, tool_handlers: ToolHandlers) -> None:
        self._settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        self._repo = repo
        self._handlers = tool_handlers

    async def chat(self, user_id: str, message: str, channel: str) -> str:
        prefs = await self._repo.get_or_create(user_id, channel)
        history = await self._repo.get_recent_history(user_id, limit=20)
        system = build_system_prompt(prefs, get_upcoming_weekend())

        messages = history + [{"role": "user", "content": message}]
        response_text = await self._agentic_loop(messages, system, user_id)

        await self._repo.append_history(user_id, "user", message)
        await self._repo.append_history(user_id, "assistant", response_text)

        return response_text

    async def _agentic_loop(self, messages: list[dict], system: str, user_id: str) -> str:
        # Use prompt caching on the system prompt to reduce latency and cost
        system_with_cache = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        while True:
            response = await self._client.messages.create(
                model=self._settings.claude_model,
                max_tokens=self._settings.max_tokens,
                system=system_with_cache,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                return _extract_text(response.content)

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._handlers.dispatch(block.name, block.input, user_id)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })

                messages.append({"role": "user", "content": tool_results})
                # Continue loop — send tool results back to Claude
            else:
                break

        return "Sorry, I encountered an unexpected issue. Please try again."
