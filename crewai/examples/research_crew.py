"""Example: a CrewAI research crew grounded on TinyFish Search + Fetch.

Run:
    export TINYFISH_API_KEY="your_api_key_here"
    export OPENAI_API_KEY="..."        # or configure any CrewAI-supported LLM
    python examples/research_crew.py

CrewAI uses LiteLLM, so swap the model below for any supported provider
(Anthropic, Google, OpenRouter, local models, and more).
"""

from crewai import LLM, Agent, Crew, Process, Task

from crewai_tinyfish import TinyFishFetchTool, TinyFishSearchTool


def build_crew(topic: str) -> Crew:
    search = TinyFishSearchTool()
    fetch = TinyFishFetchTool()
    llm = LLM(model="gpt-5.5")

    researcher = Agent(
        role="Web Researcher",
        goal=f"Gather accurate, current information about {topic} from live web sources.",
        backstory=(
            "A meticulous analyst who always searches first, then reads the most promising "
            "sources in full before drawing conclusions. Never invents facts."
        ),
        tools=[search, fetch],
        llm=llm,
        verbose=True,
    )

    writer = Agent(
        role="Briefing Writer",
        goal="Turn research notes into a crisp, well-cited briefing.",
        backstory="A writer who values clarity and always attributes claims to a source URL.",
        llm=llm,
        verbose=True,
    )

    research_task = Task(
        description=(
            f"Research '{topic}'. Use TinyFish Web Search to find the best sources, then use "
            "TinyFish Web Fetch to read the most relevant 2-3 pages in full. "
            "Collect the key facts with their source URLs."
        ),
        expected_output="A bullet list of key findings, each with a source URL.",
        agent=researcher,
    )

    write_task = Task(
        description="Write a 5-bullet executive briefing from the research findings.",
        expected_output="A 5-bullet briefing; every bullet cites a source URL.",
        agent=writer,
        context=[research_task],
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=Process.sequential,
        verbose=True,
    )


if __name__ == "__main__":
    crew = build_crew("the latest TinyFish product announcements")
    print(crew.kickoff())
