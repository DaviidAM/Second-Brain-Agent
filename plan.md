## Plan: MCP Knowledge Assistant Delivery Plan

Design and deliver an MCP server that answers like an AI assistant while grounding every response in local markdown files, enriches missing knowledge via LLM-assisted writes, and ships with a final deployment phase covering local, containerized, orchestration, and managed-cloud options.

**Steps**
1. Phase 1: Product and contract baseline ✅ COMPLETED
Define the target interaction model for AI-like responses with source-grounding, confidence scoring, and knowledge-gap handling. Freeze core API contracts for search, query, enrich, files/content, graph, list, and rescan. Mark response citation format and confidence policy as mandatory acceptance criteria.

**Deliverables**:
- API Specification (docs/API_SPECIFICATION.md): 9 endpoints with full schemas
- Response contract: ok, response, sources, confidence, gaps_detected, enrichment_triggered
- Citation model: path, snippet, relevance_score, title, last_modified, authority_score
- Confidence policy: High (≥0.9), Medium (0.7-0.9), Low (0.5-0.7), Very Low (<0.5)
- Error handling: Standard format with request_id
- Rate limiting: 120 req/sec global + per-endpoint limits
- Health/readiness endpoints for Kubernetes probes

2. Phase 2: Knowledge layer and indexing foundation (depends on 1) ✅ COMPLETED
Implement markdown repository conventions (folder taxonomy, filename policy, frontmatter schema), parser/validator, and index builders for keyword retrieval. Add optional vector index adapter behind a feature flag to support keyword-only MVP and hybrid evolution.

**Deliverables**:
- Knowledge Structure Doc (docs/KNOWLEDGE_STRUCTURE.md): architecture and conventions
- Repository structure: wiki/ + raw/ + .metadata/
- Frontmatter schema: title, author, created_at, last_modified, tags, source_type, etc.
- Tag taxonomy: 16 predefined tags (api-design, patterns, distributed-systems, etc.)
- Core modules:
  * schema.py: FrontmatterSchema, ContentValidator, RepositoryValidator (3 classes, 15+ validation rules)
  * parser.py: MarkdownParser, BulkParser, ParsedFile (extracts frontmatter, headings, wikilinks, code blocks)
  * indexing.py: KeywordIndexer, WikilinkGraphBuilder (keyword search, graph relationships, score normalization)
- Unit tests: 12+ test cases covering validation, parsing, indexing, integration
- Index metadata: keyword_index.json, graph.json serialization
- Feature-flagged vector index support (optional embedding backend)

3. Phase 3: Read pipeline for AI synthesis (depends on 2) ✅ COMPLETED
Implement query analysis, hybrid retrieval orchestration, cross-document aggregation, context window builder, and scoring normalization. Return retrieval payloads optimized for LLM prompting (ranked snippets plus metadata, links, freshness, authority).

**Deliverables**:
- Query Analysis (src/mcp/query_analyzer.py): ParsedQuery, QueryAnalyzer, QueryValidator, QueryOptimizer (4 classes)
  * Intent detection: EXPLANATION, COMPARISON, IMPLEMENTATION, TROUBLESHOOTING, REFERENCE, SYNTHESIS
  * Complexity assessment: SIMPLE, MODERATE, COMPLEX
  * Entity extraction, keyword extraction, domain detection
  * Query optimization with alternative formulations
- Retrieval Orchestration (src/mcp/retrieval.py): HybridRetriever, CrossDocumentAggregator, ScoreNormalizer, RetrievalOrchestrator (4 classes)
  * Hybrid ranking: combines keyword + vector with Reciprocal Rank Fusion
  * Cross-document aggregation with token budgeting
  * Score normalization (keyword, vector, time decay, authority boost)
  * Adaptive retrieval mode selection
- Repository Manager (src/mcp/repository.py): KnowledgeRepository, RepositoryStats (2 classes)
  * Automatic directory initialization (wiki/, .metadata/, raw/)
  * Index loading/building/persisting
  * Hybrid search coordination
  * Repository health checking
- Context Builder (src/mcp/context_builder.py): ContextBuilder, PromptBuilder, ContextValidator (3 classes)
  * Optimized context window construction for LLM
  * System + user prompt generation
  * Context quality validation
  * Token budget management
- Unit tests: 20+ test cases in tests/test_phase_3.py
  * Query analysis, validation, optimization tests
  * Score normalization tests
  * Context building tests
  * Integration pipeline tests

4. Phase 4: Write and enrichment pipeline (depends on 3) ⏳ PENDING
Implement gap detector and enrich workflow that calls an LLM agent, validates generated markdown, deduplicates/merges, and persists atomically with rollback on failure. Re-run retrieval after successful writes and regenerate final response from updated context.

5. Phase 5: AI response generation and safety controls (depends on 3 and 4) ⏳ PENDING
Implement the query endpoint orchestration: retrieve context, assess confidence, synthesize answer, attach citations, surface known gaps, and include enrichment state. Add hallucination guards (low-confidence behavior policy), max-context controls, and deterministic fallback paths.

6. Phase 6: Git automation and auditability (parallel with 5 after 4) ⏳ PENDING
Implement optional auto-commit flow for created/updated markdown with standardized commit messages and rationale trailers. Add operation logs, provenance markers, and correlation IDs across query, enrich, and write actions.

7. Phase 7: Observability, performance, and reliability hardening (parallel with 6 after 5) ⏳ PENDING
Add structured logs, metrics, health/readiness endpoints, queue/backoff controls, cache strategy, and concurrency protections. Tune for latency targets and define SLOs for query and enrich paths.

8. Phase 8: Deployment and setup phase (final, depends on 1-7) ⏳ PENDING
Package and document multiple deployment options:
- Local development: simple runbook, env setup, bootstrap scripts
- Docker single-container: image, volume strategy, health checks
- Docker Compose: API plus worker/cache/monitoring profile
- Kubernetes: manifests/Helm, secrets, PVC, autoscaling, probes
- Serverless: stateless API wrapper, object storage backing, cold-start constraints
- Managed cloud: Cloud Run/App Runner style container deployment
Include a decision matrix, prerequisites, security checklist, environment-variable matrix, migration path, and rollback strategy.

**Relevant files**
- /Users/dalbama1/david/projects/Second-Brain-Agent/prompt.md — source requirements and architectural constraints used to derive the implementation plan.
- /Users/dalbama1/david/projects/Second-Brain-Agent/README.md — project-level onboarding and setup anchor for deployment/runbook integration.

**Verification**
1. Contract verification: validate API schemas and examples against required fields for response, sources, confidence, gaps_detected, enrichment flags, and status codes.
2. Retrieval quality tests: run query suites covering exact, fuzzy, and multi-document questions; verify ranking quality and citation relevance.
3. Enrichment correctness tests: simulate empty/partial knowledge scenarios and verify generated markdown, deduplication outcomes, and atomic write guarantees.
4. Safety checks: run low-confidence and contradiction scenarios to verify guarded responses and explicit uncertainty behavior.
5. Performance tests: measure p95 query latency under expected concurrency and ensure cache/index settings meet target thresholds.
6. Git automation tests: verify commit behavior, message templates, and failure rollback when commit or write steps fail.
7. Deployment validation: run smoke tests for each deployment option and confirm health/readiness, storage access, secret loading, and observability endpoints.

**Decisions**
- Included scope: AI-like grounded response engine, markdown knowledge lifecycle, LLM enrichment loop, optional git auto-commit, and multi-path deployment strategy.
- Excluded scope: custom UI product, multi-tenant billing, and non-markdown primary storage as first-class backend.
- Default retrieval strategy: keyword-first with optional vector augmentation; hybrid enabled where embeddings are configured.

**Further Considerations**
1. Confidence policy recommendation: block hard answers below threshold for high-risk domains, otherwise answer with uncertainty plus citations.
2. Model policy recommendation: cost-tiered model routing (cheap model for gap triage, stronger model for final synthesis/enrichment).
3. Deployment recommendation: start with Docker Compose for team adoption, then move to Kubernetes only when autoscaling and tenancy are required.
4. Index-based search strategy: Utilize persistent `.metadata/` indices for fast full-text search and graph navigation
   - `index.json`: Keyword index enables sub-100ms searches across large wiki repositories
   - `graph.json`: Wikilink relationship graph for traversing connected documents
   - `.embeddings.index` (optional): Vector embeddings for semantic search when enabled
5. Obsidian-like wiki experience: Design future frontend/UI layer to provide knowledge graph visualization similar to Obsidian
   - Graph view: Interactive visualization of wikilink connections between documents
   - Bi-directional links: Show which documents reference the current page
   - Full-text search: Leverage keyword index for instant search results with highlighting
   - Backlinks panel: Navigate relationships between related documents
   - Tag explorer: Browse documents by taxonomy tags with filtering
   - Autocomplete: Type to find wikilinks with document preview
   - Note these are UI features that would consume the existing API endpoints (GET /graph, POST /search, GET /files/content)
