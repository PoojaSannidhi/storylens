"""
app.py — StoryLens Gradio UI

Two-step flow:
  Step 1: Generate book → stream agent activity → show PDF preview + download
  Step 2: Human reads book → clicks Approve or Reject
          Approve → send email
          Reject  → discard
"""

from dotenv import load_dotenv
from pathlib import Path
import os

# load_dotenv MUST be before any crewai imports
dotenv_path = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(dotenv_path=dotenv_path, override=True)

import queue
import threading
import gradio as gr
from storylens.crew import StoryLensCrew, CREW_DONE
from storylens.tools.email_tools import send_email


# ── State — stores generated book between Step 1 and Step 2 ──────────────────
# Gradio state keeps this per-session
def initial_state():
    return {
        "pdf_path": None,
        "book_title": None,
        "child_name": None,
        "email": None,
    }


# ── Step 1 — Generate the book ────────────────────────────────────────────────

def generate_book(
    topic: str,
    child_name: str,
    age: str,
    appearance: str,
    style: str,
    email: str,
    state: dict,
):
    """
    Runs StoryLens crew in background thread.
    Streams progress to activity log.
    Returns final activity + book preview + updated state.
    """
    if not topic.strip() or not child_name.strip() or not age.strip():
        yield (
            "❌ Please fill in topic, child name, and age.",
            "",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            state,
        )
        return

    progress_queue = queue.Queue()
    result_holder = {"result": None, "error": None, "pdf_path": None}
    activity_log = []

    inputs = {
        "topic":      topic.strip(),
        "child_name": child_name.strip(),
        "age":        age.strip(),
        "appearance": appearance.strip() or f"a cute {age} year old child",
        "style":      style or "fun and rhyming",
        "email":      email.strip(),
        "num_pages":  "10",
    }

    def run_crew():
        try:
            crew = StoryLensCrew(progress_queue=progress_queue).crew()
            result_holder["result"] = crew.kickoff(inputs=inputs)
        except Exception as e:
            result_holder["error"] = str(e)
        finally:
            progress_queue.put(CREW_DONE)

    thread = threading.Thread(target=run_crew, daemon=True)
    thread.start()

    # Initial yield
    yield (
        f"🚀 Generating book for **{child_name}**...\n📖 Topic: {topic}",
        "",
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        state,
    )

    # Stream progress
    while True:
        try:
            message = progress_queue.get(timeout=1.0)
        except queue.Empty:
            if not thread.is_alive() and progress_queue.empty():
                break
            continue

        if message == CREW_DONE:
            break

        activity_log.append(message)
        yield (
            "\n".join(activity_log),
            "",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            state,
        )

    thread.join(timeout=5)

    if result_holder["error"]:
        yield (
            "\n".join(activity_log) + f"\n\n❌ Error: {result_holder['error']}",
            "",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            state,
        )
        return

    # Find PDF path — check output folder
    # crewai run executes from project root so output/ is relative to that
    pdf_path = None
    project_root = Path(__file__).resolve().parents[2]  # storylens/
    safe_name = child_name.strip().lower().replace(" ", "_")

    # Check multiple possible locations
    candidates = [
        project_root / "output" / f"{safe_name}_storylens_book.pdf",
        Path("output") / f"{safe_name}_storylens_book.pdf",
        Path(f"output/{safe_name}_storylens_book.pdf"),
    ]

    for candidate in candidates:
        if candidate.exists():
            pdf_path = str(candidate)
            break

    if not pdf_path:
        # Search any output folder for latest PDF
        for output_dir in [project_root / "output", Path("output")]:
            if output_dir.exists():
                pdfs = sorted(output_dir.glob("*.pdf"), key=os.path.getmtime)
                if pdfs:
                    pdf_path = str(pdfs[-1])
                    break

    print(f"PDF search: safe_name={safe_name}, found={pdf_path}")

    if pdf_path:
        # Update state for Step 2
        state["pdf_path"] = pdf_path
        state["book_title"] = topic
        state["child_name"] = child_name.strip()
        state["email"] = email.strip()

        final_activity = "\n".join(activity_log) + "\n\n✅ Book generated! Review below and approve to send."

        yield (
            final_activity,
            f"## 📚 {child_name}'s Book is Ready!\n\nReview the PDF below, then click **Approve** to email it.",
            gr.update(visible=True, value=pdf_path),   # PDF viewer
            gr.update(visible=True),                    # Approve button
            gr.update(visible=True),                    # Reject button
            state,
        )
    else:
        yield (
            "\n".join(activity_log) + "\n\n⚠️ Book generated but PDF not found.",
            "",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            state,
        )


# ── Step 2a — Approve ─────────────────────────────────────────────────────────

def approve_book(state: dict):
    """Send the book via email after human approval."""
    pdf_path   = state.get("pdf_path")
    book_title = state.get("book_title", "Your Book")
    child_name = state.get("child_name", "")
    email      = state.get("email", "")

    if not pdf_path or not os.path.exists(pdf_path):
        return (
            "❌ PDF not found — cannot send email.",
            gr.update(visible=False),
            gr.update(visible=False),
        )

    if not email:
        return (
            "✅ Book approved! No email address provided — PDF saved locally.",
            gr.update(visible=False),
            gr.update(visible=False),
        )

    # Send email
    result = send_email.run(
        to_email=email,
        book_title=book_title,
        child_name=child_name,
        pdf_path=pdf_path,
    )

    if isinstance(result, dict) and result.get("status") == "success":
        return (
            f"✅ Book approved and emailed to **{email}**! 🎉\n\nCheck your inbox for {child_name}'s book.",
            gr.update(visible=False),
            gr.update(visible=False),
        )
    else:
        return (
            f"✅ Book approved! PDF saved at `{pdf_path}`\n\n(Email delivery: {result})",
            gr.update(visible=False),
            gr.update(visible=False),
        )


# ── Step 2b — Reject ──────────────────────────────────────────────────────────

def reject_book(state: dict):
    """Discard the book."""
    state["pdf_path"] = None
    return (
        "❌ Book rejected. You can generate a new one with different settings.",
        gr.update(visible=False),
        gr.update(visible=False),
    )


# ── Gradio UI ──────────────────────────────────────────────────────────────────

with gr.Blocks(theme=gr.themes.Soft()) as ui:
    gr.Markdown(
        """
        # 📚 StoryLens
        ### AI-Powered Personalized Children's Book Generator
        **Powered by CrewAI** · 6 agents · memory · reasoning · guardrails · human-in-the-loop
        """
    )

    # Session state
    book_state = gr.State(initial_state())

    with gr.Row():

        # ── Left panel — inputs ───────────────────────────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### 📝 Book Details")

            topic = gr.Textbox(
                label="Book Topic",
                placeholder="e.g. Animals of the Jungle, Good Bedtime Habits",
            )
            child_name = gr.Textbox(
                label="Child's Name",
                placeholder="e.g. Aryan",
            )
            age = gr.Textbox(
                label="Child's Age",
                placeholder="e.g. 3",
            )
            appearance = gr.Textbox(
                label="Child's Appearance (for illustrations)",
                placeholder="e.g. curly black hair, brown eyes, round face",
                lines=2,
            )
            style = gr.Dropdown(
                label="Story Style",
                choices=[
                    "fun and rhyming",
                    "gentle and calming",
                    "adventurous and exciting",
                    "funny and silly",
                    "warm and educational",
                ],
                value="fun and rhyming",
            )
            email_input = gr.Textbox(
                label="Email (receive the finished book)",
                placeholder="you@example.com",
            )

            generate_btn = gr.Button(
                "✨ Generate Book →",
                variant="primary",
                size="lg",
            )

            gr.Markdown(
                """
                ---
                **What happens:**
                1. 💡 Idea agent plans the story arc
                2. ✍️  Writer agent writes 10 pages
                3. 🎨 Illustrator generates DALL-E images
                4. 🔍 Continuity agent checks consistency
                5. 📝 Copy reviewer checks language
                6. 📄 PDF generated for your review
                7. ✅ **You approve** → book emailed to you
                """
            )

        # ── Right panel — output ──────────────────────────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 Agent Activity")
            activity = gr.Textbox(
                label="Live Pipeline Progress",
                lines=10,
                interactive=False,
                placeholder="Agent activity will stream here...",
            )

            status = gr.Markdown(
                value="*Your book will appear here once generated...*"
            )

            # PDF viewer — hidden until book is ready
            pdf_viewer = gr.File(
                label="📖 Download & Review Your Book",
                visible=False,
                file_types=[".pdf"],
            )

            # Approval buttons — hidden until book is ready
            with gr.Row():
                approve_btn = gr.Button(
                    "✅ Approve & Send Email",
                    variant="primary",
                    visible=False,
                )
                reject_btn = gr.Button(
                    "❌ Reject & Regenerate",
                    variant="stop",
                    visible=False,
                )

    # ── Event handlers ────────────────────────────────────────────────────────

    generate_btn.click(
        fn=generate_book,
        inputs=[topic, child_name, age, appearance, style, email_input, book_state],
        outputs=[activity, status, pdf_viewer, approve_btn, reject_btn, book_state],
    )

    approve_btn.click(
        fn=approve_book,
        inputs=[book_state],
        outputs=[status, approve_btn, reject_btn],
    )

    reject_btn.click(
        fn=reject_book,
        inputs=[book_state],
        outputs=[status, approve_btn, reject_btn],
    )

ui.queue().launch()