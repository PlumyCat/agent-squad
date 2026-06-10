# Twitch Tutorial Extractor

Project for extracting Twitch video tutorials (without audio) into text documentation.

## Context

This project extracts content from video tutorials using:
1. **ffmpeg** to extract frames from the video
2. **Azure OpenAI GPT-4.1-mini** (vision) to analyze frames and extract text

## Video Source

Twitch tutorial by @claudecodeonly on creating a **Multi-Claude Bootstrap** system:
- URL: https://www.twitch.tv/claudecodeonly/video/2657952550
- Duration: ~6 hours
- Content: Multi-agent Claude orchestration system with tmux

## Structure

```
twich-test/
├── .env                    # Azure credentials (DO NOT COMMIT)
├── .gitignore
├── requirements.txt
├── extract_frames.py       # Main extraction script
├── CLAUDE.md              # This file
└── output/                # Extraction results (generated)
```

## Usage

### 1. Download the video and extract frames

```bash
# Download
yt-dlp -o video.mp4 "https://www.twitch.tv/claudecodeonly/video/2657952550"

# Extract frames (1 every 5 seconds)
mkdir -p frames
ffmpeg -i video.mp4 -vf "fps=1/5" -q:v 2 frames/frame_%05d.jpg
```

### 2. Extract content with Azure

```bash
# Install dependencies
pip install -r requirements.txt

# Extract (1 frame per minute by default)
python extract_frames.py --frames-dir ./frames --output tutorial.md

# Options
python extract_frames.py \
  --frames-dir ./frames \
  --output tutorial.md \
  --sample-rate 6 \        # 1 frame every 30 sec
  --start-frame 100 \      # Start at frame 100
  --end-frame 500          # End at frame 500
```

## Azure Configuration

The `.env` file contains:
- `AZURE_OPENAI_ENDPOINT`: Azure Foundry endpoint
- `AZURE_OPENAI_API_KEY`: API key
- `AZURE_OPENAI_DEPLOYMENT`: Deployment name (gpt-4.1-mini)

## Tutorial Content (preliminary summary)

The tutorial covers creating a multi-agent Claude system:

### Architecture
- **Squad Orchestrator**: Main orchestrator, human interface
- **Workers**: Delegated agents in separate tmux sessions
- **Managers**: Middle-manager, stream-manager for coordination

### Components
- `claude-cli`: Python CLI to spawn/manage workers
- `context-cli`: Role and directive management
- `tickets-cli`: Ticket system for task tracking

### Key Concepts
- Tmux sessions to isolate workers
- CLAUDE.md for context persistence
- YAML roles (orchestrator.yaml, worker.yaml)
- Reusable modular directives
- Named Claudes with canonical memories

## Source Frames

Extracted frames are stored in:
```
/tmp/claude/-home-eric-cc-config/07a4be6d-7f6d-4615-9097-be0ecb6f02c7/scratchpad/twitch_frames/frames/
```

Total: 4344 frames (~6h of video at 5 sec intervals)
