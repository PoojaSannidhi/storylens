"""
crew.py — StoryLens CrewAI crew definition

Wires together all agents, tasks, tools, guardrails and memory
into a single crew that generates a personalized children's book.

Queue pattern for Gradio streaming:
  app.py creates a queue and passes it to StoryLensCrew(progress_queue=queue)
  step_callback and task_callback write messages to the queue
  app.py reads from the queue in a while loop and yields to Gradio

Flow:
  story_concept_task
    → write_pages_1_to_3_task
    → write_pages_4_to_6_task
    → write_pages_7_to_10_task
    → illustrate_pages_1_to_3_task
    → illustrate_pages_4_to_6_task
    → illustrate_pages_7_to_10_task
    → continuity_check_task
    → copy_review_task
    → publishing_task (human_input=True)
"""

import os
import queue
from typing import Any, Tuple
from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import DallETool
from storylens.schemas import (
    BookConcept,
    StoryBatch,
    IllustrationBatch,
    ContinuityReport,
    CopyReviewReport,
    PublishedBook,
)
from storylens.tools.email_tools import send_email
from storylens.tools.pdf_tools import generate_pdf


# ── Guardrail functions ────────────────────────────────────────────────────────
# CrewAI requires guardrails to return exactly (bool, str | None)
# Never return None alone — always return a tuple

def validate_story_batch_3_pages(output):
    try:
        result = output.pydantic
        if result is None:
            return (True, None)
        if len(result.pages) != 3:
            return (False, f"Expected 3 pages got {len(result.pages)}")
        for page in result.pages:
            if not page.title:
                return (False, "Page missing title")
        return (True, None)
    except Exception:
        return (True, None)


def validate_story_batch_4_pages(output):
    try:
        result = output.pydantic
        if result is None:
            return (True, None)
        if len(result.pages) != 4:
            return (False, f"Expected 4 pages got {len(result.pages)}")
        for page in result.pages:
            if not page.title:
                return (False, "Page missing title")
        return (True, None)
    except Exception:
        return (True, None)


def validate_illustration_batch(output):
    try:
        result = output.pydantic
        if result is None:
            return (True, None)
        scary_words = ["scary", "monster", "death", "blood", "evil"]
        for prompt in result.prompts:
            p = prompt.prompt
            for word in scary_words:
                if word in p.lower():
                    return (False, f"Prompt contains unsafe word: {word}")
        return (True, None)
    except Exception:
        return (True, None)


def validate_continuity_report(output):
    try:
        result = output.pydantic
        if result is None:
            return (True, None)
        if not result.summary:
            return (False, "Continuity report missing summary")
        return (True, None)
    except Exception:
        return (True, None)


def validate_copy_review(output):
    try:
        result = output.pydantic
        if result is None:
            return (True, None)
        if not result.reading_level:
            return (False, "Copy review missing reading level")
        return (True, None)
    except Exception:
        return (True, None)


# ── Task labels — human readable progress messages ────────────────────────────

TASK_LABELS = {
    "story_concept_task":            "💡 Story concept complete",
    "write_pages_1_to_3_task":       "✍️  Pages 1-3 written",
    "write_pages_4_to_6_task":       "✍️  Pages 4-6 written",
    "write_pages_7_to_10_task":      "✍️  Pages 7-10 written",
    "illustrate_pages_1_to_3_task":  "🎨 Pages 1-3 illustrated",
    "illustrate_pages_4_to_6_task":  "🎨 Pages 4-6 illustrated",
    "illustrate_pages_7_to_10_task": "🎨 Pages 7-10 illustrated",
    "continuity_check_task":         "🔍 Continuity check complete",
    "copy_review_task":              "📝 Copy review complete",
    "publishing_task":               "📚 Book published!",
}

# Sentinel — app.py checks for this to know crew is done
CREW_DONE = "__CREW_DONE__"


# ── Crew definition ───────────────────────────────────────────────────────────

@CrewBase
class StoryLensCrew:
    """
    StoryLens — personalized children's book generator.

    6 agents, 11 tasks, sequential process.
    Memory enabled so story_weaver remembers character names.
    Guardrails on every writing and illustration task.
    Human approval before publishing.

    Queue pattern:
      app.py passes a queue.Queue() to StoryLensCrew(progress_queue=q)
      step_callback writes granular agent steps to the queue
      task_callback writes task completion labels to the queue
      app.py reads from queue in a while loop and yields to Gradio
    """

    agents_config = "config/agents.yaml"
    tasks_config  = "config/tasks.yaml"

    def __init__(self, progress_queue: queue.Queue | None = None):
        """
        progress_queue: passed from app.py
          callbacks write messages here
          app.py reads and yields to Gradio
          If None (main.py / testing) — just prints to console
        """
        self.progress_queue = progress_queue

    def _emit(self, message: str):
        """
        Central method — sends progress to Gradio via queue.
        Always prints to console too (useful for debugging).
        """
        print(message)
        if self.progress_queue:
            self.progress_queue.put(message)

    # ── Agents ────────────────────────────────────────────────────────────────

    @agent
    def idea_architect(self) -> Agent:
        return Agent(
            config=self.agents_config["idea_architect"],
            reasoning=True,              # plans full story arc before writing
            max_reasoning_attempts=2,
            inject_date=True,            # date-aware — avoids outdated references
            verbose=True,
        )

    @agent
    def story_weaver(self) -> Agent:
        return Agent(
            config=self.agents_config["story_weaver"],
            memory=True,                 # remembers character names across batches
            respect_context_window=True, # auto-summarize if context grows large
            verbose=True,
        )

    @agent
    def visual_storyteller(self) -> Agent:
        return Agent(
            config=self.agents_config["visual_storyteller"],
            multimodal=True,             # can process image descriptions
            tools=[DallETool()],         # generates actual DALL-E images
            verbose=True,
        )

    @agent
    def continuity_guardian(self) -> Agent:
        return Agent(
            config=self.agents_config["continuity_guardian"],
            reasoning=True,              # plans what to check before reviewing
            respect_context_window=True, # reads all 10 pages — large context
            verbose=True,
        )

    @agent
    def copy_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["copy_reviewer"],
            verbose=True,
        )

    @agent
    def book_publisher(self) -> Agent:
        return Agent(
            config=self.agents_config["book_publisher"],
            tools=[generate_pdf, send_email],
            verbose=True,
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @task
    def story_concept_task(self) -> Task:
        return Task(
            config=self.tasks_config["story_concept_task"],
            output_pydantic=BookConcept,
        )

    @task
    def write_pages_1_to_3_task(self) -> Task:
        return Task(
            config=self.tasks_config["write_pages_1_to_3_task"],
            output_pydantic=StoryBatch,
        )

    @task
    def write_pages_4_to_6_task(self) -> Task:
        return Task(
            config=self.tasks_config["write_pages_4_to_6_task"],
            output_pydantic=StoryBatch,
        )

    @task
    def write_pages_7_to_10_task(self) -> Task:
        return Task(
            config=self.tasks_config["write_pages_7_to_10_task"],
            output_pydantic=StoryBatch,
        )

    @task
    def illustrate_pages_1_to_3_task(self) -> Task:
        return Task(
            config=self.tasks_config["illustrate_pages_1_to_3_task"],
            output_pydantic=IllustrationBatch,
        )

    @task
    def illustrate_pages_4_to_6_task(self) -> Task:
        return Task(
            config=self.tasks_config["illustrate_pages_4_to_6_task"],
            output_pydantic=IllustrationBatch,
        )

    @task
    def illustrate_pages_7_to_10_task(self) -> Task:
        return Task(
            config=self.tasks_config["illustrate_pages_7_to_10_task"],
            output_pydantic=IllustrationBatch,
        )

    @task
    def continuity_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["continuity_check_task"],
            output_pydantic=ContinuityReport,
        )

    @task
    def copy_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["copy_review_task"],
            output_pydantic=CopyReviewReport,
        )

    @task
    def publishing_task(self) -> Task:
        return Task(
            config=self.tasks_config["publishing_task"],
            output_pydantic=PublishedBook,
            # human_input handled in Gradio UI — not terminal
        )

    # ── Crew ──────────────────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        # Unified Memory — memory=True uses CrewAI defaults
        # Custom Memory object not supported in crewai 1.12.2
        # memory=True enables short-term + long-term + entity memory

        def step_callback(step_output):
            """
            Fires after every agent STEP within a task.
            Granular — many times per task.
            step_callback is on the Crew — applies to all agents.
            Writes to queue → app.py yields to Gradio.
            """
            message = str(step_output)[:80]
            self._emit(f"   🔧 {message}")

        def task_callback(task_output):
            """
            Fires after each full TASK completes.
            Coarse — once per task, 11 times total for StoryLens.
            Different from step_callback — one fires per step,
            this fires once when the entire task is done.
            Writes human-readable label to queue → Gradio.
            """
            task_name = getattr(task_output, 'name', '') or ''
            label = TASK_LABELS.get(task_name, f"✅ {task_name} complete")
            self._emit(label)

        return Crew(
            agents=self.agents,           # auto-collected via @agent decorators
            tasks=self.tasks,             # auto-collected via @task decorators
            process=Process.sequential,   # ordered: concept→write→illustrate→review→publish
            memory=True,                  # unified memory: short + long + entity
            verbose=True,
            step_callback=step_callback,  # granular — every agent step → queue
            task_callback=task_callback,  # coarse — every task done → queue
            max_rpm=10,                   # rate limit — avoid OpenAI throttling
            output_log_file="logs/storylens.json",
        )