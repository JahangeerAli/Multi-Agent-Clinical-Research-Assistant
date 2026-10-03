import json
import re
import time
from crewai import Agent, Task, Crew, Process, LLM
import config

# ---------------------------------------------------------------------------
# Compatibility patch: newer CrewAI versions add extra keys to messages
# (like "cache_breakpoint") that Groq rejects. We remove them just before
# the request is sent.
# ---------------------------------------------------------------------------
try:
    import litellm

    _BAD_MESSAGE_KEYS = {"cache_breakpoint", "cache_control"}
    _BAD_CALL_KEYS = {"is_litellm"}

    if not getattr(litellm.completion, "_groq_patched", False):
        _original_completion = litellm.completion

        def _patched_completion(*args, **kwargs):
            messages = kwargs.get("messages")
            if messages:
                kwargs["messages"] = [
                    {k: v for k, v in m.items() if k not in _BAD_MESSAGE_KEYS}
                    if isinstance(m, dict) else m
                    for m in messages
                ]
            for key in _BAD_CALL_KEYS:
                kwargs.pop(key, None)
            return _original_completion(*args, **kwargs)

        _patched_completion._groq_patched = True
        litellm.completion = _patched_completion
except Exception:
    pass  # if litellm is missing, nothing to patch


def make_llm(model, temperature=0.2, max_tokens=1500):
    """CrewAI LLM object pointing at Groq."""
    return LLM(model=model, api_key=config.GROQ_API_KEY,
               temperature=temperature, max_tokens=max_tokens)


def make_agent(role, goal, backstory, model, tools=None, max_iter=5,
               temperature=0.2, max_tokens=1500):
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=make_llm(model, temperature, max_tokens),
        tools=tools or [],
        allow_delegation=False,
        verbose=False,
        max_iter=max_iter,
    )


def run_task(agent, description, expected_output, retries=3):
    """Run one CrewAI task with one agent. Retries on Groq free-tier rate limits."""
    for attempt in range(retries):
        try:
            task = Task(description=description,
                        expected_output=expected_output,
                        agent=agent)
            crew = Crew(agents=[agent], tasks=[task],
                        process=Process.sequential, verbose=False)
            result = crew.kickoff()
            return getattr(result, "raw", None) or str(result)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(8 * (attempt + 1))


def parse_json(text):
    """Pull a JSON object out of the model's reply. Returns {} if it fails."""
    try:
        text = re.sub(r"```(?:json)?", "", text or "")
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end + 1])
    except Exception:
        return {}
