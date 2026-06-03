import json
import logging

import anthropic

from sydney_planner.agent.prompts import build_system_prompt
from sydney_planner.agent.tool_handlers import ToolHandlers
from sydney_planner.agent.tools import TOOLS
from sydney_planner.config import get_settings
from sydney_planner.memory.repository import UserPreferencesRepository
from sydney_planner.utils.date_helpers import get_upcoming_weekend

logger = logging.getLogger(__name__)

# Maximum tool-use iterations per turn to prevent infinite loops
MAX_TOOL_ITERATIONS = 10


def _extract_text(content: list) -> str:
    parts = [block.text for block in content if hasattr(block, "text")]
    return "\n".join(parts).strip()


class PlannerAgent:
    def __init__(self, repo: UserPreferencesRepository, tool_handlers: ToolHandlers) -> None:
        self._settings = get_settings()
        if not self._settings.anthropic_api_key or self._settings.anthropic_api_key == "sk-ant-...":
            raise ValueError(
                "ANTHROPIC_API_KEY is not configured. "
                "Copy .env.example to .env and add your real API key from console.anthropic.com"
            )
        self._client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        self._repo = repo
        self._handlers = tool_handlers
        logger.info("PlannerAgent initialised (model=%s)", self._settings.claude_model)

    async def chat(self, user_id: str, message: str, channel: str) -> str:
        """Main entry point for all channels. Returns the agent's text reply."""
        try:
            prefs = await self._repo.get_or_create(user_id, channel)
            history = await self._repo.get_recent_history(user_id, limit=20)
            system = build_system_prompt(prefs, get_upcoming_weekend())

            messages = history + [{"role": "user", "content": message}]
            response_text = await self._agentic_loop(messages, system, user_id)

            await self._repo.append_history(user_id, "user", message)
            await self._repo.append_history(user_id, "assistant", response_text)

            return response_text

        except anthropic.AuthenticationError:
            logger.error("Anthropic authentication failed — check ANTHROPIC_API_KEY in .env")
            return (
                "⚠️ The agent isn't configured yet — the API key is missing or invalid. "
                "Please contact the administrator."
            )
        except anthropic.RateLimitError:
            logger.warning("Anthropic rate limit hit for user %s", user_id)
            return (
                "I'm a bit busy right now — you've hit the rate limit. "
                "Please wait a moment and try again! 🙏"
            )
        except anthropic.APIConnectionError:
            logger.error("Cannot reach Anthropic API")
            return (
                "I can't reach my planning brain right now (network issue). "
                "Please try again in a few seconds."
            )
        except Exception as exc:
            logger.exception("Unexpected error in chat() for user %s: %s", user_id, exc)
            return "Something unexpected went wrong. Please try again shortly."

    async def _agentic_loop(self, messages: list[dict], system: str, user_id: str) -> str:
        """
        Tool-use loop: POST to Claude → handle tool_use blocks → repeat until end_turn.
        Capped at MAX_TOOL_ITERATIONS to prevent runaway loops.
        """
        system_with_cache = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = await self._client.messages.create(
                model=self._settings.claude_model,
                max_tokens=self._settings.max_tokens,
                system=system_with_cache,
                tools=TOOLS,
                messages=messages,
            )

            logger.debug(
                "Claude response: stop_reason=%s iterations=%d user=%s",
                response.stop_reason, iteration + 1, user_id,
            )

            if response.stop_reason == "end_turn":
                return _extract_text(response.content)

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.debug("Executing tool: %s args=%s", block.name, block.input)
                        result = await self._handlers.dispatch(block.name, block.input, user_id)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })

                messages.append({"role": "user", "content": tool_results})

            else:
                logger.warning("Unexpected stop_reason=%s", response.stop_reason)
                break

        logger.error("Exceeded MAX_TOOL_ITERATIONS (%d) for user %s", MAX_TOOL_ITERATIONS, user_id)
        return "I got a bit carried away planning — please try asking again!"
