# AI Coach setup

## Purpose

The local-first AI Coach uses available profile, Tracker.gg, recent match, and safe monitor data to generate coaching notes.

## Optional configuration

### `.streamlit/secrets.toml`

```toml
OPENAI_API_KEY = "your_openai_api_key"
```

### Environment variable

```bash
set OPENAI_API_KEY=your_openai_api_key
```

## Fallback behavior

If the OpenAI key is missing or the API is unavailable, the coach returns a local fallback report with safe recommendations based on the available dashboard data.

## Safety note

The coach must not invent missing stats. It should clearly say when data is unavailable and keep recommendations tied to profile, match log, tracker, and monitor context.
