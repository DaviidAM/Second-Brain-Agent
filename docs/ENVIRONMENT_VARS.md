# Environment Variables

## Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | `sk-...` |
| `LLM_BASE_URL` | Custom LLM endpoint | `https://api.openai.com/v1` |

## Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WIKI_PATH` | `knowledge/wiki` | Path to wiki directory |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_TOKENS` | `8000` | Max context tokens |
| `RATE_LIMIT` | `120` | Requests per second |
| `CACHE_SIZE` | `1000` | Query cache size |
| `EMBEDDING_CACHE_SIZE` | `5000` | Embedding cache size |
| `GIT_AUTO_COMMIT` | `false` | Enable auto-commit |
| `ENABLE_ENRICHMENT` | `true` | Enable LLM enrichment |
| `DEFAULT_MODEL` | `gpt-4o-mini` | Default LLM model |
| `TEMPERATURE` | `0.7` | LLM temperature |

## Secret Variables (use secrets management)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | API key for LLM |
| `DATABASE_URL` | No | PostgreSQL connection string |
| `REDIS_URL` | No | Redis connection string |

## Docker Variables

```bash
# docker-compose.yml environment section
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - WIKI_PATH=/data/wiki
  - LOG_LEVEL=INFO
```

## Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-secrets
type: Opaque
stringData:
  OPENAI_API_KEY: your-api-key
```
