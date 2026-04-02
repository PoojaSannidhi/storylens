---
title: StoryLens
emoji: 📚
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 4.44.1
app_file: src/storylens/app.py
pinned: false
---

# 📚 StoryLens — AI Personalized Children's Book Generator

StoryLens uses 6 CrewAI agents to write, illustrate, and publish a personalized 10-page children's book with DALL-E illustrations.

## How it works
1. 💡 Idea Architect — plans the story arc
2. ✍️ Story Weaver — writes rhyming text for all 10 pages
3. 🎨 Visual Storyteller — generates DALL-E illustrations
4. 🔍 Continuity Guardian — checks consistency
5. 📝 Copy Reviewer — checks grammar and age-appropriateness
6. 📚 Book Publisher — assembles illustrated PDF

## Setup
Add these secrets in Space settings:
- `OPENAI_API_KEY`
- `SENDGRID_API_KEY`
- `SENDGRID_FROM_EMAIL`