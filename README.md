---
title: Songless Telugu
emoji: 🎵
colorFrom: yellow
colorTo: red
sdk: gradio
app_file: app.py
pinned: false
---

# Songless Telugu

Guess Telugu songs from a few seconds of audio. Anyone can play: no login, no Premium.

## Setup (one time)
1. Get a free YouTube Data API key: Google Cloud Console, create a project, enable **YouTube Data API v3**, then Credentials, **Create API key**.
2. Set it as `YOUTUBE_API_KEY` (Hugging Face: Space Settings, **Secrets**; locally: `export YOUTUBE_API_KEY=...`).
3. Run `pip install -r requirements.txt && python app.py`, or upload these files to a Gradio Space.

The key stays on the server. Each song costs one search the first time it is used (100 of the free 10,000 daily quota units) and is remembered afterwards.
To pin a song to a specific video, add its YouTube ID as a third item on its line in `app.py`.
