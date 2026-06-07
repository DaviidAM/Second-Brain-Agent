# Local Development Setup

## Prerequisites

- Python 3.10 or higher
- Git
- OpenAI API key (for LLM enrichment)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Second-Brain-Agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export WIKI_PATH="knowledge/wiki"
   ```

5. **Initialize knowledge base**
   ```bash
   python -m src.mcp.schema --init
   ```

6. **Run development server**
   ```bash
   python -m src.mcp.server
   ```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for LLM calls |
| `WIKI_PATH` | No | `knowledge/wiki` | Path to wiki directory |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `MAX_TOKENS` | No | `8000` | Max context tokens |
| `RATE_LIMIT` | No | `120` | Requests per second |

## Bootstrap Script

Run the bootstrap script for quick setup:
```bash
bash scripts/bootstrap.sh
```

## Development Server

Start the server with auto-reload:
```bash
python -m uvicorn src.mcp.server:app --reload
```

## Testing

Run tests:
```bash
pytest tests/ -v
```

Run specific phase tests:
```bash
pytest tests/test_phase_4.py -v
```
