# API Specification - Phase 1: Product & Contract Baseline

## Overview
This document defines the complete API contract for the MCP Knowledge Assistant server. All endpoints return structured JSON responses with consistent error handling and citation models.

---

## Core Interaction Model

### Response Characteristics
All successful responses must include:
- **response**: Natural language answer grounded in local documents
- **sources**: List of documents used with path, snippet, and relevance score
- **confidence**: Score 0-1 indicating how well local knowledge covers the query
- **gaps_detected**: List of identified knowledge gaps
- **enrichment_triggered**: Boolean indicating if LLM enrichment was initiated
- **enrichment_status**: `pending|completed|failed` (only when enrichment_triggered=true)

### Citation Model
Every source must include:
```json
{
  "path": "wiki/topic/subtopic.md",
  "snippet": "Relevant excerpt from document...",
  "relevance_score": 0.92,
  "title": "Document Title",
  "last_modified": "2026-06-07T10:30:00Z",
  "authority_score": 0.85
}
```

### Confidence Policy
- **≥ 0.9**: High confidence - answer with authority, cite sources
- **0.7-0.9**: Medium confidence - answer with supporting sources, note gaps
- **0.5-0.7**: Low confidence - answer with explicit uncertainty, mark gaps as critical
- **< 0.5**: Very low confidence - defer to enrichment or explicit "knowledge gap" response

---

## Endpoints

### 1. POST /search
Query the knowledge base using hybrid retrieval (keyword + optional vector).

**Request:**
```json
{
  "query": "How to implement retry logic in distributed systems?",
  "top_k": 5,
  "search_mode": "hybrid",
  "include_content": false,
  "filters": {
    "min_confidence": 0.5,
    "max_age_days": 90
  }
}
```

**Response (200 OK):**
```json
{
  "ok": true,
  "results": [
    {
      "path": "wiki/distributed-systems/retry-patterns.md",
      "title": "Retry Patterns in Distributed Systems",
      "snippet": "Exponential backoff with jitter is the recommended approach...",
      "relevance_score": 0.94,
      "vector_score": 0.89,
      "mode": "hybrid",
      "last_modified": "2026-05-15T08:00:00Z",
      "authority_score": 0.9
    },
    {
      "path": "wiki/patterns/fault-tolerance.md",
      "title": "Fault Tolerance Design Patterns",
      "snippet": "Retry logic must include circuit breaker patterns...",
      "relevance_score": 0.78,
      "vector_score": 0.82,
      "mode": "hybrid",
      "last_modified": "2026-04-20T14:30:00Z",
      "authority_score": 0.75
    }
  ],
  "search_mode": "hybrid",
  "total_results": 2,
  "query_tokens": 8,
  "execution_time_ms": 125
}
```

**Error Responses:**
- **400 Bad Request**: Empty query, invalid search_mode
- **429 Too Many Requests**: Rate limit exceeded (120 req/sec)
- **503 Service Unavailable**: Search service overloaded

---

### 2. POST /query
Generate an AI-like response grounded in local documents with automatic enrichment.

**Request:**
```json
{
  "query": "What are best practices for API versioning?",
  "context_limit": 3000,
  "confidence_threshold": 0.6,
  "auto_enrich": true,
  "enrich_on_gaps": true
}
```

**Response (200 OK):**
```json
{
  "ok": true,
  "response": "API versioning strategies depend on your API's maturity and user base. The most common approaches are URL-based versioning (v1, v2 in the path), header-based versioning, and semantic versioning. URL-based versioning is the most explicit and cacheable, making it ideal for public APIs. However, it requires more planning for backward compatibility. Header-based versioning is less discoverable but cleaner in URLs. The key is to maintain backward compatibility for N-1 versions and provide clear deprecation timelines.",
  "sources": [
    {
      "path": "wiki/api-design/versioning-strategies.md",
      "snippet": "URL-based versioning is the most explicit approach, typically using /v1/, /v2/ patterns...",
      "relevance_score": 0.96,
      "title": "API Versioning Strategies",
      "last_modified": "2026-05-10T09:15:00Z",
      "authority_score": 0.92
    },
    {
      "path": "wiki/patterns/backward-compatibility.md",
      "snippet": "Maintain N-1 version support and provide explicit deprecation timelines...",
      "relevance_score": 0.84,
      "title": "Backward Compatibility Patterns",
      "last_modified": "2026-03-20T16:45:00Z",
      "authority_score": 0.88
    }
  ],
  "confidence": 0.91,
  "gaps_detected": [
    "Specific example of header-based versioning implementation",
    "Cost/performance trade-offs between versioning strategies"
  ],
  "enrichment_triggered": false,
  "enrichment_status": null,
  "execution_time_ms": 245
}
```

**Response with Enrichment (200 OK):**
```json
{
  "ok": true,
  "response": "...[enhanced response]...",
  "sources": [
    "...existing sources...",
    {
      "path": "wiki/api-design/versioning-header-example.md",
      "snippet": "Header-based versioning uses Accept-Version or API-Version headers...",
      "relevance_score": 0.85,
      "title": "Header-Based Versioning Example",
      "last_modified": "2026-06-07T10:30:00Z",
      "authority_score": 0.70
    }
  ],
  "confidence": 0.94,
  "gaps_detected": [],
  "enrichment_triggered": true,
  "enrichment_status": "completed",
  "enriched_files": [
    "wiki/api-design/versioning-header-example.md"
  ],
  "execution_time_ms": 3200
}
```

**Error Responses:**
- **400 Bad Request**: Invalid context_limit, confidence_threshold out of range
- **422 Unprocessable Entity**: Query too complex or malformed
- **500 Internal Server Error**: LLM enrichment failed (will retry)

---

### 3. GET /files/content
Retrieve full markdown content of a specific file.

**Request:**
```
GET /files/content?path=wiki/api-design/versioning-strategies.md
```

**Response (200 OK):**
```json
{
  "ok": true,
  "path": "wiki/api-design/versioning-strategies.md",
  "content": "---\ntitle: API Versioning Strategies\nauthor: knowledge-system\ncreated_at: 2026-05-10T09:15:00Z\ntags:\n  - api-design\n  - versioning\n  - best-practices\nrelations:\n  - wiki/patterns/backward-compatibility.md\n  - wiki/api-design/deprecation-policy.md\n---\n\n# API Versioning Strategies\n\n## Overview\nAPI versioning...",
  "metadata": {
    "title": "API Versioning Strategies",
    "created_at": "2026-05-10T09:15:00Z",
    "last_modified": "2026-05-10T09:15:00Z",
    "author": "knowledge-system",
    "tags": ["api-design", "versioning", "best-practices"],
    "size_bytes": 4251
  },
  "word_count": 856,
  "links": {
    "internal": [
      {
        "target": "wiki/patterns/backward-compatibility.md",
        "anchor": null,
        "text": "backward compatibility patterns"
      }
    ],
    "external": []
  }
}
```

**Error Responses:**
- **404 Not Found**: File does not exist
- **403 Forbidden**: Path traversal attempt or out-of-bounds path
- **413 Payload Too Large**: File exceeds 2MB

---

### 4. GET /graph
Retrieve knowledge graph with wikilinks and relationships.

**Request:**
```
GET /graph?limit=200&q=versioning&nodeType=concept
```

**Response (200 OK):**
```json
{
  "ok": true,
  "nodes": [
    {
      "id": "wiki/api-design/versioning-strategies.md",
      "label": "API Versioning Strategies",
      "nodeType": "concept",
      "path": "wiki/api-design/versioning-strategies.md",
      "linkCount": 5,
      "tags": ["api-design", "versioning"]
    },
    {
      "id": "wiki/patterns/backward-compatibility.md",
      "label": "Backward Compatibility Patterns",
      "nodeType": "pattern",
      "path": "wiki/patterns/backward-compatibility.md",
      "linkCount": 8,
      "tags": ["patterns", "compatibility"]
    }
  ],
  "edges": [
    {
      "source": "wiki/api-design/versioning-strategies.md",
      "target": "wiki/patterns/backward-compatibility.md",
      "weight": 1,
      "type": "references"
    }
  ],
  "stats": {
    "total_nodes": 2,
    "total_edges": 1,
    "query_matched_nodes": 2
  }
}
```

**Error Responses:**
- **400 Bad Request**: Invalid limit, nodeType, or query
- **413 Payload Too Large**: Graph exceeds 10,000 nodes (return 413 with limit guidance)

---

### 5. GET /list
List knowledge base structure as a tree.

**Request:**
```
GET /list?root=wiki&recursive=true&maxFiles=2000
```

**Response (200 OK):**
```json
{
  "ok": true,
  "tree": {
    "name": "wiki",
    "isDir": true,
    "children": [
      {
        "name": "api-design",
        "isDir": true,
        "size": 18340,
        "children": [
          {
            "name": "versioning-strategies.md",
            "isDir": false,
            "size": 4251,
            "lastModified": "2026-05-10T09:15:00Z"
          }
        ]
      },
      {
        "name": "patterns",
        "isDir": true,
        "size": 45230,
        "children": []
      }
    ]
  },
  "totalFiles": 42,
  "totalSize": 1250000
}
```

**Error Responses:**
- **400 Bad Request**: Invalid root, maxFiles out of range
- **413 Payload Too Large**: Tree exceeds 10,000 nodes

---

### 6. POST /enrich
Manually trigger knowledge enrichment for a topic.

**Request:**
```json
{
  "query": "Explain circuit breaker pattern in microservices",
  "action": "create_or_update",
  "priority": "high",
  "tags": ["patterns", "microservices", "resilience"],
  "relations": [
    "wiki/patterns/retry-logic.md",
    "wiki/patterns/fallback-patterns.md"
  ]
}
```

**Response (202 Accepted - Async):**
```json
{
  "ok": true,
  "enrichment_id": "enrich_1718000000_abc123",
  "status": "queued",
  "query": "Explain circuit breaker pattern in microservices",
  "estimated_completion_seconds": 15,
  "created_files": [],
  "updated_files": [],
  "confidence": null
}
```

**Status Check - GET /enrich/{enrichment_id}:**
```json
{
  "ok": true,
  "enrichment_id": "enrich_1718000000_abc123",
  "status": "completed",
  "created_files": [
    "wiki/patterns/circuit-breaker.md"
  ],
  "updated_files": [],
  "confidence": 0.87,
  "generated_content_quality": 0.89,
  "completion_time_ms": 12450
}
```

**Error Responses:**
- **400 Bad Request**: Invalid action, missing required fields
- **429 Too Many Requests**: Enrichment queue full
- **503 Service Unavailable**: LLM service unavailable

---

### 7. POST /sources/rescan
Rebuild indices after manual edits to markdown files.

**Request:**
```json
{
  "full_reindex": false,
  "paths": ["wiki/api-design"]
}
```

**Response (202 Accepted):**
```json
{
  "ok": true,
  "rescan_id": "rescan_1718000000_xyz789",
  "status": "queued",
  "affected_paths": ["wiki/api-design"],
  "files_to_process": 12,
  "estimated_time_seconds": 8
}
```

**Status Check - GET /rescan/{rescan_id}:**
```json
{
  "ok": true,
  "rescan_id": "rescan_1718000000_xyz789",
  "status": "completed",
  "files_processed": 12,
  "files_added": 0,
  "files_updated": 3,
  "files_deleted": 0,
  "index_updated": true,
  "completion_time_ms": 7250
}
```

---

## Health & Readiness Endpoints

### GET /health
Server liveness probe (always available, no deps check).

**Response (200 OK):**
```json
{
  "ok": true,
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-06-07T10:30:00Z"
}
```

### GET /ready
Readiness probe (checks all dependencies).

**Response (200 OK):**
```json
{
  "ok": true,
  "status": "ready",
  "checks": {
    "knowledge_base": "ok",
    "search_index": "ok",
    "llm_service": "ok",
    "git_repository": "ok"
  }
}
```

**Response (503 Service Unavailable):**
```json
{
  "ok": false,
  "status": "not_ready",
  "checks": {
    "knowledge_base": "ok",
    "search_index": "error",
    "llm_service": "ok",
    "git_repository": "timeout"
  },
  "message": "Search index initialization in progress"
}
```

---

## Error Handling

### Standard Error Response Format
```json
{
  "ok": false,
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "value that caused error",
    "suggestion": "how to fix it"
  },
  "request_id": "req_xyz789",
  "timestamp": "2026-06-07T10:30:00Z"
}
```

### HTTP Status Codes
| Code | Meaning | Retry? |
|------|---------|--------|
| 200 | Success | No |
| 202 | Accepted (async) | No |
| 400 | Bad Request | No |
| 401 | Unauthorized | No |
| 403 | Forbidden | No |
| 404 | Not Found | No |
| 409 | Conflict (duplicate) | Maybe |
| 413 | Payload Too Large | No |
| 429 | Rate Limited | Yes (with backoff) |
| 500 | Internal Error | Yes (with backoff) |
| 503 | Service Unavailable | Yes (with backoff) |

---

## Rate Limiting
- **Global**: 120 requests/second
- **Per endpoint**: /search (30/s), /query (20/s), /enrich (5/s)
- **Response headers**: 
  - `RateLimit-Limit: 120`
  - `RateLimit-Remaining: 85`
  - `RateLimit-Reset: 1718000060`

---

## Authentication (Future - Phase 3)
- Token-based via `Authorization: Bearer <token>` header
- Or environment variable `KNOWLEDGE_API_TOKEN`

---

## Mandatory Acceptance Criteria (Phase 1)
- [ ] All endpoints return consistent JSON structure with `ok` field
- [ ] All success responses include `sources`, `confidence`, and citation metadata
- [ ] All error responses include `error`, `message`, and `request_id`
- [ ] Citation format includes path, snippet, relevance_score, and authority_score
- [ ] Confidence scoring follows defined policy (≥0.9 high, 0.7-0.9 medium, etc.)
- [ ] Query endpoint supports both synchronous and asynchronous enrichment
- [ ] Rate limiting headers present on all responses
- [ ] Health/readiness endpoints follow Kubernetes probe conventions
