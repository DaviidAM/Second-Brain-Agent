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

**Deliverables**:
- Gap Detection (src/mcp/gap_detector.py): GapDetector, GapClassifier, GapPrioritizer (3 classes)
  * Identify knowledge gaps from confidence scores and missing content signals
  * Classify gaps: missing_definition, incomplete_comparison, outdated_info, missing_example, unknown_topic
  * Prioritize gaps based on query relevance and user intent
  * Generate gap summaries for LLM enrichment prompts
- LLM Enrichment Client (src/mcp/enrichment_client.py): EnrichmentClient, PromptTemplateManager, ResponseValidator (3 classes)
  * Call external LLM API with structured prompts containing gap context
  * Template management for different gap types (definition, comparison, implementation, etc.)
  * Validate LLM responses for format compliance and content quality
  * Configurable model selection and temperature settings
- Deduplication and Merge Engine (src/mcp/merge_engine.py): MergeEngine, ContentDeduplicator, ConflictResolver (3 classes)
  * Detect duplicate or near-duplicate content in knowledge base
  * Merge strategies: append, replace, preserve, hybrid
  * Conflict detection and resolution for overlapping information
  * Semantic deduplication using embeddings when available
- Atomic Write Manager (src/mcp/write_manager.py): WriteManager, TransactionLog, RollbackHandler (3 classes)
  * Atomic file operations with temporary files and atomic rename
  * Transaction logging for failure recovery
  * Rollback on failure with cleanup of partial writes
  * Write confirmation and error reporting
- Enrichment Orchestrator (src/mcp/enrichment_orchestrator.py): EnrichmentOrchestrator, EnrichmentStateTracker (2 classes)
  * Coordinate gap detection → LLM call → validation → merge → write flow
  * Track enrichment state across requests
  * Re-run retrieval after successful writes
  * Generate final response from updated context
- Unit tests: 15+ test cases in tests/test_phase_4.py
  * Gap detection and classification tests
  * LLM response validation tests
  * Merge and deduplication tests
  * Atomic write and rollback tests
  * End-to-end enrichment flow tests

5. Phase 5: AI response generation and safety controls (depends on 3 and 4) ⏳ PENDING
Implement the query endpoint orchestration: retrieve context, assess confidence, synthesize answer, attach citations, surface known gaps, and include enrichment state. Add hallucination guards (low-confidence behavior policy), max-context controls, and deterministic fallback paths.

**Deliverables**:
- Query Orchestration (src/mcp/query_orchestrator.py): QueryOrchestrator, ResponseBuilder, ConfidenceAssessor (3 classes)
  * Coordinate retrieval → confidence assessment → synthesis → citation flow
  * Build structured response with all required fields
  * Confidence threshold checking and gap detection integration
  * Response serialization to API contract format
- Response Synthesis (src/mcp/synthesis.py): ResponseSynthesizer, PromptBuilder, CitationAttacher (3 classes)
  * Generate natural language responses from retrieved context
  * Build LLM prompts with retrieved snippets, metadata, and instructions
  * Attach citations with relevance scores and authority indicators
  * Format gaps and enrichment status in response
- Hallucination Guards (src/mcp/hallucination_guard.py): HallucinationGuard, ClaimValidator, UncertaintyHandler (3 classes)
  * Validate claims against source material
  * Detect ungrounded statements in LLM output
  * Inject uncertainty markers for low-confidence content
  * Block or warn on high-risk unverified claims
- Context Window Manager (src/mcp/context_manager.py): ContextManager, TokenBudgetController, TruncationStrategy (3 classes)
  * Enforce max-context limits based on model constraints
  * Token budgeting across retrieved snippets
  * Intelligent truncation with priority ranking
  * Preserve citation metadata during truncation
- Fallback Paths (src/mcp/fallback_handler.py): FallbackHandler, DeterministicResponseGenerator, ErrorResponseBuilder (3 classes)
  * Deterministic responses for known query patterns
  * Graceful degradation on LLM failures
  * Error response standardization
  * Cached response fallback for repeated queries
- Unit tests: 15+ test cases in tests/test_phase_5.py
  * Orchestration flow tests
  * Synthesis and citation tests
  * Hallucination detection tests
  * Context limit enforcement tests
  * Fallback path tests

6. Phase 6: Git automation and auditability (parallel with 5 after 4) ⏳ PENDING
Implement optional auto-commit flow for created/updated markdown with standardized commit messages and rationale trailers. Add operation logs, provenance markers, and correlation IDs across query, enrich, and write actions.

**Deliverables**:
- Git Auto-Commit (src/mcp/git_automation.py): GitAutoCommit, CommitMessageGenerator, CommitPolicy (3 classes)
  * Optional auto-commit on successful enrichment writes
  * Standardized commit message templates: "[enrich] Add: {title}", "[enrich] Update: {title}", "[merge] Merge: {title}"
  * Rationale trailers: `<!-- enrichment_rationale: {reason} -->`, `<!-- provenance: {correlation_id} -->`
  * Configurable commit behavior (enable/disable per operation)
- Operation Logging (src/mcp/operation_logger.py): OperationLogger, LogFormatter, AuditTrail (3 classes)
  * Structured logging of all query, enrich, and write operations
  * JSON format with timestamps, correlation IDs, user context
  * Audit trail persistence to .metadata/audit/
  * Log rotation and retention policies
- Provenance Tracking (src/mcp/provenance.py): ProvenanceTracker, CorrelationManager, LineageRecorder (3 classes)
  * Generate and track correlation IDs across request lifecycle
  * Record provenance: source_query, enrichment_triggered, llm_model, generation_time
  * Link original queries to enriched content
  * Support audit queries for compliance
- Unit tests: 10+ test cases in tests/test_phase_6.py
  * Commit message generation tests
  * Commit policy enforcement tests
  * Operation logging tests
  * Correlation ID propagation tests

7. Phase 7: Observability, performance, and reliability hardening (parallel with 6 after 5) ⏳ PENDING
Add structured logs, metrics, health/readiness endpoints, queue/backoff controls, cache strategy, and concurrency protections. Tune for latency targets and define SLOs for query and enrich paths.

**Deliverables**:
- Structured Logging (src/mcp/logging_config.py): StructuredLogger, LogContext, RequestLogger (3 classes)
  * JSON structured logging with contextual fields
  * Request/response logging with timing
  * Error context capture and stack traces
  * Configurable log levels per component
- Metrics Collection (src/mcp/metrics.py): MetricsCollector, QueryMetrics, EnrichmentMetrics (3 classes)
  * Query latency histograms (p50, p95, p99)
  * Enrichment success/failure rates
  * Token usage tracking
  * Cache hit/miss ratios
  * Custom metrics for business logic
- Health Endpoints (src/mcp/health.py): HealthChecker, ReadinessProbe, LivenessProbe (3 classes)
  * GET /health: liveness check for Kubernetes
  * GET /ready: readiness check with dependency verification
  * Health checks: index available, repository accessible, LLM client configured
  * Detailed status with component-level health
- Rate Limiting and Backoff (src/mcp/rate_limiter.py): RateLimiter, TokenBucket, BackoffStrategy (3 classes)
  * Global rate limit enforcement (120 req/sec)
  * Per-endpoint rate limits
  * Exponential backoff for retryable errors
  * Circuit breaker for external dependencies
- Cache Strategy (src/mcp/cache.py): CacheManager, QueryCache, EmbeddingCache (2 classes)
  * LRU cache for frequent queries
  * Cache invalidation on index updates
  * TTL-based expiration
  * Cache metrics and monitoring
- Concurrency Protection (src/mcp/concurrency.py): ConcurrencyManager, SemaphorePool, RequestQueue (3 classes)
  * Semaphore-based concurrency limits
  * Request queuing for burst handling
  * Timeout enforcement
  * Deadlock prevention
- SLO Definitions (docs/SLO.md):
  * Query path: p95 < 500ms (cache), p95 < 2s (full retrieval)
  * Enrichment path: p95 < 10s (including LLM call)
  * Availability: 99.9% uptime
  * Error rate: < 1% for query, < 5% for enrichment
- Unit tests: 12+ test cases in tests/test_phase_7.py
  * Health check tests
  * Rate limiting tests
  * Cache behavior tests
  * Concurrency tests

8. Phase 8: Deployment and setup phase (final, depends on 1-7) ⏳ PENDING
Package and document multiple deployment options:
- Local development: simple runbook, env setup, bootstrap scripts
- Docker single-container: image, volume strategy, health checks
- Docker Compose: API plus worker/cache/monitoring profile
- Kubernetes: manifests/Helm, secrets, PVC, autoscaling, probes
- Serverless: stateless API wrapper, object storage backing, cold-start constraints
- Managed cloud: Cloud Run/App Runner style container deployment
Include a decision matrix, prerequisites, security checklist, environment-variable matrix, migration path, and rollback strategy.

**Deliverables**:
- Local Development Setup (docs/LOCAL_SETUP.md):
  * Python 3.10+ environment setup
  * Virtual environment creation
  * Environment variables configuration
  * Bootstrap script: scripts/bootstrap.sh
  * Quick start runbook
  * Development server startup
- Docker Single Container (docker/Dockerfile):
  * Multi-stage build for minimal image size
  * Non-root user for security
  * Health check endpoint
  * Volume mounting for wiki/ directory
  * Resource limits configuration
- Docker Compose Setup (docker-compose.yml):
  * API service with environment configuration
  * Redis cache service
  * Optional monitoring (Prometheus/Grafana)
  * Volume configuration for persistence
  * Health checks for all services
- Kubernetes Manifests (k8s/):
  * Deployment with replicas and resource limits
  * Service and Ingress configuration
  * ConfigMap for non-secret config
  * Secret for API keys and tokens
  * PVC for wiki/ storage
  * HPA for autoscaling
  * Liveness and readiness probes
  * Helm chart in charts/mcp-server/
- Serverless Configuration (serverless/):
  * AWS Lambda / Cloud Functions handler
  * API Gateway integration
  * S3 bucket for wiki/ storage
  * Cold-start optimization
  * Timeout and memory configuration
- Managed Cloud Deployment (cloud/):
  * Cloud Run deployment configuration
  * App Runner configuration
  * Container registry setup
  * Environment variable management
  * IAM role configuration
- Decision Matrix (docs/DEPLOYMENT_DECISION.md):
  * Comparison table: local vs Docker vs K8s vs serverless vs managed
  * Decision criteria: team size, scaling needs,运维 complexity, cost
  * Recommended paths by use case
- Environment Variable Matrix (docs/ENVIRONMENT_VARS.md):
  * All configurable environment variables
  * Default values and required flags
  * Description and example values
  * Secret vs non-secret classification
- Security Checklist (docs/SECURITY_CHECKLIST.md):
  * API key management
  * Network policies
  * Container security
  * Data encryption at rest
  * Audit logging requirements
- Migration Path (docs/MIGRATION.md):
  * Upgrade procedure between versions
  * Data migration for wiki/ structure changes
  * Configuration migration
  * Rollback procedure
- Rollback Strategy (docs/ROLLBACK.md):
  * Version rollback steps
  * Database/index rollback
  * Configuration rollback
  * Emergency contact procedures

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
