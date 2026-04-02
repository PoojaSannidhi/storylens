"""
models/schemas.py

Pydantic models for StoryLens.
Every agent returns a typed structured output — no raw string blobs.

Flow:
  BookConcept          → idea_architect output
  StoryPage            → story_weaver output (per batch)
  IllustrationPrompt   → visual_storyteller output (per batch)
  ContinuityReport     → continuity_guardian output
  CopyReviewReport     → copy_reviewer output
  PublishedBook        → book_publisher output
"""

from pydantic import BaseModel, Field


# ── Idea Architect Output ──────────────────────────────────────────────────────

class PageConcept(BaseModel):
    page_number: int = Field(description="Page number 1-10")
    title: str = Field(description="Creative page title — no colons no numbering")
    story_event: str = Field(description="What happens on this page")
    moral_thread: str = Field(description="The lesson or moral woven into this page")
    characters: list[str] = Field(description="Characters appearing on this page")


class BookConcept(BaseModel):
    book_title: str = Field(description="The title of the children's book")
    child_name: str = Field(description="The child who is the hero")
    topic: str = Field(description="The topic of the book")
    central_moral: str = Field(description="The overall moral of the book in one sentence")
    arc_description: str = Field(description="Brief description of the story arc across 10 pages")
    pages: list[PageConcept] = Field(description="Exactly 10 page concepts")


# ── Story Weaver Output ────────────────────────────────────────────────────────

class StoryPage(BaseModel):
    page_number: int = Field(description="Page number 1-10")
    title: str = Field(description="Page title matching the concept")
    text: str = Field(description="Story text for this page — 2 to 4 short sentences")
    rhymes: bool = Field(description="True if this page uses rhyming")


class StoryBatch(BaseModel):
    pages: list[StoryPage] = Field(description="Story pages in this batch")


# ── Visual Storyteller Output ──────────────────────────────────────────────────

class IllustrationPrompt(BaseModel):
    page_number: int = Field(description="Page number 1-10")
    prompt: str = Field(
        description=(
            "Detailed DALL-E image generation prompt. "
            "Must include child's appearance, scene, art style, "
            "color palette. Safe for toddlers."
        )
    )
    scene_description: str = Field(description="Plain English description of what the illustration shows")


class IllustrationBatch(BaseModel):
    prompts: list[IllustrationPrompt] = Field(description="Illustration prompts in this batch")


# ── Continuity Guardian Output ─────────────────────────────────────────────────

class ContinuityIssue(BaseModel):
    page_number: int = Field(description="Page where the issue was found")
    issue_type: str = Field(description="One of: character | plot | visual | age_appropriateness")
    description: str = Field(description="What the issue is")
    correction: str = Field(description="How to fix it")


class ContinuityReport(BaseModel):
    passed: bool = Field(description="True if no issues found")
    issues: list[ContinuityIssue] = Field(
        default_factory=list,
        description="List of continuity issues found. Empty if passed."
    )
    summary: str = Field(description="One sentence summary of the continuity check result")


# ── Copy Reviewer Output ───────────────────────────────────────────────────────

class PageCorrection(BaseModel):
    page_number: int = Field(description="Page that needs correction")
    issue: str = Field(description="What was wrong")
    original_text: str = Field(description="The original text")
    corrected_text: str = Field(description="The corrected text")


class CopyReviewReport(BaseModel):
    passed: bool = Field(description="True if no corrections needed")
    corrections: list[PageCorrection] = Field(
        default_factory=list,
        description="List of page corrections. Empty if passed."
    )
    reading_level: str = Field(description="Assessed reading level e.g. age 2-4")
    summary: str = Field(description="One sentence summary of the copy review result")


# ── Book Publisher Output ──────────────────────────────────────────────────────

class PublishedBook(BaseModel):
    book_title: str = Field(description="Title of the published book")
    child_name: str = Field(description="The child hero of the book")
    page_count: int = Field(description="Total number of pages")
    pdf_path: str = Field(description="Path to the generated PDF file")
    email_sent_to: str = Field(description="Email address the book was sent to")
    status: str = Field(description="One of: success | failed")
    message: str = Field(description="Confirmation message or error details")