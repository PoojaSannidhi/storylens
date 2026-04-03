#!/usr/bin/env python
"""
main.py — StoryLens entry point

Run directly for local testing:
  python main.py

For Gradio UI:
  python app.py
"""

import sys
import warnings
from dotenv import load_dotenv
from storylens.crew import StoryLensCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Run the StoryLens crew with sample inputs.
    Used for local testing without Gradio UI.
    """
    inputs = {
        "topic":      "Animals of the Jungle",
        "child_name": "Aryan",
        "age":        "3",
        "appearance": "curly black hair, brown eyes, round face, age 3",
        "style":      "fun and rhyming",
        "email":      "sannidhipooja@gmail.com",
        "num_pages":  "10",
    }

    try:
        result = StoryLensCrew().crew().kickoff(inputs=inputs)
        print("\n✅ Book generation complete!")
        print(f"Book title: {result.pydantic.book_title if result.pydantic else 'N/A'}")
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")