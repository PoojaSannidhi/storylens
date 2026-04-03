---
title: StoryLens
emoji: 📚
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 5.23.3
app_file: src/storylens/app.py
pinned: false
python_version: "3.11"
---

# 📚 StoryLens — AI Personalized Children's Book Generator

StoryLens uses 6 CrewAI agents to write, illustrate, and publish a personalized 10-page children's book with DALL-E illustrations.

## Setup
Add these secrets in Space settings:
- `OPENAI_API_KEY`
- `SENDGRID_API_KEY`
- `SENDGRID_FROM_EMAIL`
