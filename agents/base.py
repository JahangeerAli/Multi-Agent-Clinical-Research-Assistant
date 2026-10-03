import json
import re
import time
from crewai import Agent, Task, Crew, Process, LLM
import config


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
