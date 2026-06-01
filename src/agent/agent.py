import ast
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

FINAL_ANSWER_RE = re.compile(r"Final Answer:\s*(.+)", re.IGNORECASE | re.DOTALL)
ACTION_RE = re.compile(r"Action:\s*(\w+)\s*\((.*)\)\s*$", re.IGNORECASE | re.MULTILINE)
THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?=\n(?:Action:|Final Answer:)|\Z)", re.IGNORECASE | re.DOTALL)


class ReActAgent:
    """ReAct agent for multi-platform resort review analysis."""

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 6):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history: List[str] = []
        self._tool_map: Dict[str, Callable[..., str]] = {
            t["name"]: t["func"] for t in tools
        }

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(f"- {t['name']}: {t['description']}" for t in self.tools)
        tool_names = ", ".join(t["name"] for t in self.tools)
        return f"""You are an AI operations analyst for Sunrise Bay Resort.
Guest reviews come from TripAdvisor, Booking, Google, Agoda, and social media (mock dataset).

You MUST use tools for facts, quotes, counts, and comparisons. Do not invent review text.

Available tools:
{tool_descriptions}

Allowed tool names only: {tool_names}

Respond using EXACTLY this format (one step at a time):
Thought: <reasoning>
Action: tool_name(arg1, arg2)   OR   Action: tool_name("single_arg")

After you receive Observation lines in the conversation, continue with another Thought/Action OR finish with:
Final Answer: <clear summary with priorities for management, cite aspects and quotes when available>

Rules:
- Use double quotes for string arguments.
- Use top_issues for recurring complaints; search_reviews for specific aspect/keyword.
- Use sentiment_summary when asked about overall tone of one aspect (room, breakfast, etc.).
- When enough evidence is gathered, output Final Answer (do not call more tools).
- LANGUAGE: Write every Final Answer in Vietnamese (tiếng Việt). Thought lines may be Vietnamese too.
  Guest review quotes may stay in original English/Vietnamese; all explanation and recommendations must be in Vietnamese."""

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        self.history = [f"User question: {user_input}"]
        steps = 0
        final_answer: Optional[str] = None

        while steps < self.max_steps:
            prompt = "\n\n".join(self.history)
            result = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=result.get("latency_ms", 0),
            )
            text = (result.get("content") or "").strip()
            logger.log_event("AGENT_STEP", {"step": steps + 1, "raw_output": text[:2000]})

            thought = self._extract_thought(text)
            if thought:
                self.history.append(f"Thought: {thought}")

            final_match = FINAL_ANSWER_RE.search(text)
            if final_match:
                final_answer = final_match.group(1).strip()
                logger.log_event("AGENT_FINAL", {"step": steps + 1, "answer_preview": final_answer[:500]})
                break

            action = self._extract_action(text)
            if action:
                tool_name, arg_str = action
                observation = self._execute_tool(tool_name, arg_str)
                self.history.append(f"Action: {tool_name}({arg_str})")
                self.history.append(f"Observation: {observation}")
                logger.log_event("TOOL_CALL", {"tool": tool_name, "args": arg_str, "ok": not observation.startswith("Error")})
            else:
                self.history.append(
                    "Observation: Error: Could not parse Action. "
                    "Use format Action: tool_name(\"arg\") then wait for observation."
                )
                logger.log_event("PARSE_ERROR", {"step": steps + 1, "message": "no_action_or_final"})

            steps += 1

        if not final_answer:
            final_answer = (
                "Could not complete within step limit. "
                "Partial context:\n" + "\n".join(self.history[-4:])
            )
            logger.log_event("AGENT_TIMEOUT", {"steps": steps})

        logger.log_event("AGENT_END", {"steps": steps, "completed": final_answer is not None})
        return final_answer

    @staticmethod
    def _extract_thought(text: str) -> Optional[str]:
        match = THOUGHT_RE.search(text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_action(text: str) -> Optional[Tuple[str, str]]:
        matches = list(ACTION_RE.finditer(text))
        if not matches:
            return None
        last = matches[-1]
        return last.group(1), last.group(2).strip()

    def _parse_args(self, arg_str: str) -> Tuple[List[Any], Dict[str, Any]]:
        arg_str = arg_str.strip()
        if not arg_str:
            return [], {}

        if "=" in arg_str and not arg_str.startswith(('"', "'")):
            kwargs: Dict[str, Any] = {}
            for part in re.split(r",\s*(?=\w+=)", arg_str):
                if "=" not in part:
                    continue
                key, val = part.split("=", 1)
                kwargs[key.strip()] = ast.literal_eval(val.strip())
            return [], kwargs

        try:
            parsed = ast.literal_eval(f"({arg_str},)" if "," in arg_str else f"({arg_str})")
            if isinstance(parsed, tuple):
                return list(parsed), {}
        except (SyntaxError, ValueError):
            pass

        return [arg_str.strip("\"'")], {}

    def _execute_tool(self, tool_name: str, args: str) -> str:
        func = self._tool_map.get(tool_name)
        if not func:
            return f"Error: Tool '{tool_name}' not found. Allowed: {', '.join(self._tool_map)}"

        try:
            positional, kwargs = self._parse_args(args)
            return str(func(*positional, **kwargs))
        except Exception as exc:
            return f"Error executing {tool_name}: {exc}"
