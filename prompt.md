# Professional MCP Architecture Request Prompt

## Request: Design and Implementation Plan for Knowledge Management MCP Server

### Executive Summary
I need a comprehensive architectural plan and implementation strategy for a Model Context Protocol (MCP) server that functions as an intelligent, self-evolving knowledge management system. This MCP will serve as a bridge between AI agents and a markdown-based knowledge repository, enabling:

- **Contextual AI Responses**: Generate AI-like responses grounded in local markdown files as authoritative knowledge source
- **Semantic Search**: Enable intelligent queries over the knowledge base with keyword and vector similarity
- **Intelligent Gap Detection**: Identify missing knowledge and automatically enrich the repository
- **Automated Knowledge Enrichment**: Call LLM agents to create/update markdown files when gaps are detected

The MCP should behave like a knowledgeable AI assistant that:
1. **Consults local documents first** before generating responses (ensuring accuracy and consistency)
2. **Provides contextual answers** citing relevant local files as sources
3. **Learns continuously** by detecting gaps and enriching the knowledge base
4. **Maintains coherent reasoning** by using the entire knowledge base as persistent context
5. **Avoids hallucination** by grounding all responses in existing or newly-created local knowledge

---

## Core Requirements

### 0. **AI Response Generation Model** (Primary Behavior)
The MCP must act as an **AI-like assistant powered by local knowledge**:

- **User Query → Local Context Pipeline**:
  1. User poses a question or request
  2. MCP searches local markdown files for relevant context
  3. MCP retrieves ranked results with confidence scores
  4. MCP synthesizes an intelligent response using retrieved documents as authoritative source
  5. Response includes citations to relevant local files for verification

- **Response Characteristics**:
  - Natural language generation similar to ChatGPT/Claude (coherent, contextual, helpful)
  - Every claim grounded in local markdown files with explicit citations
  - Confidence levels tied to source document quality/recency
  - Ability to reason across multiple documents to provide comprehensive answers
  - Clear acknowledgment of knowledge gaps when local files don't cover a topic

- **Fallback Behavior** (when knowledge gap detected):
  - Explicitly state what information is missing
  - Trigger LLM agent to create new markdown content
  - After enrichment, regenerate response with new knowledge
  - Store decision rationale for future learning

### 1. **Knowledge Base Architecture**
- **Storage Medium**: Markdown files organized in a hierarchical directory structure (similar to the LLM Wiki pattern)
- **File Organization**: Logical categorization by topic/domain with clear naming conventions
- **Metadata Support**: Frontmatter (YAML) for tagging, relationships, timestamps, and version control markers
- **Scalability**: Support for thousands of documents without performance degradation

### 2. **Read Operations (Query & Retrieval for AI Synthesis)**
- **Semantic Search for Context Gathering**: When an AI agent queries a topic, the MCP must:
  - Search existing markdown files by keyword and semantic similarity
  - Return ranked results with relevance scoring (top 3-5 most relevant documents)
  - Provide file content, snippets, and metadata for context window
  - Support hybrid search (keyword + vector embeddings when available)
  - Enable cross-document reasoning for complex queries (retrieve multiple related documents)

- **Resolution Pattern for AI-Ready Context**: 
  - Check local filesystem first for existing knowledge (source of truth)
  - Aggregate results from multiple documents when topic spans several files
  - Return structured context (path, title, content, score, relationships) optimized for LLM input
  - Support cross-referencing and wikilink traversal to build comprehensive context
  - Compute confidence scores based on document quality, recency, and relevance
  - Return "partial knowledge" responses when some data is found (trigger enrichment for gaps)
  - Format results as clean markdown for direct use in AI system prompts

### 3. **Write Operations (Knowledge Enrichment)**
- **Gap Detection**: When search results are incomplete or absent:
  - Trigger an LLM agent call to generate missing knowledge
  - LLM evaluates whether to create new files or update existing ones
  - LLM generates contextually appropriate markdown content
- **File Creation/Modification**:
  - Atomic write operations with rollback capability
  - Automatic frontmatter generation (creation date, topic tags, relationships)
  - Validation of markdown syntax before persistence
  - Prevent duplicates and conflicting content

### 4. **LLM Integration Layer (Continuous Knowledge Enhancement)**
- **Agent Invocation for Gap Filling**: When local knowledge is insufficient, MCP calls an LLM agent with:
  - User's original query for context
  - Retrieved local documents (what knowledge already exists)
  - Explicit gap description (what information is missing)
  - Instructions for content generation with specific quality/format constraints
  - Domain-specific tone and style derived from existing local documents
  - Constraints for avoiding duplication or contradicting existing knowledge
  
- **AI-Augmented Response Loop**:
  - LLM generates markdown content based on the query + local context
  - Content is validated against existing knowledge for consistency
  - New/updated files are persisted to knowledge base
  - MCP then re-queries to provide enriched response using both old + new knowledge
  - User sees enhanced response that feels like increased AI knowledge
  
- **Feedback Loop**: Store all LLM-generated content with:
  - Confidence/quality scores for future filtering
  - Linkage to user query that triggered creation
  - Versioning markers for knowledge evolution
  - Implicit feedback signals (was this content useful? accurate?)

- **Context Preservation**: Maintain full conversation history in metadata for:
  - Understanding knowledge creation context
  - Detecting redundant or contradictory future generations
  - Improving prompt quality for LLM calls over time

### 5. **Git Integration (Phase 1 Future)**
- **Automated Commits**: 
  - Track all write operations
  - Auto-commit new/modified files with descriptive commit messages
  - Include change rationale in commit bodies (sourced from LLM decision logs)
- **Version History**: Maintain full git history for knowledge evolution tracking
- **Branching Strategy**: Support feature branches for experimental knowledge domains

---

## Technical Specifications

### API Surface
- **Primary Endpoints**:
  - `POST /search` — Query the knowledge base (keyword + vector)
  - `GET /files/content` — Read file content by path
  - `GET /graph` — Retrieve knowledge graph (wikilinks relationships)
  - `POST /enrich` — Trigger gap-filling workflow (calls LLM agent)
  - `POST /query` — **NEW** — AI-synthesized response using local context
  - `GET /list` — Tree view of knowledge structure
  - `POST /sources/rescan` — Rebuild indices after manual edits

- **New Endpoint: `/query` (AI Response Generation)**
  - Request: `{ "query": "user question", "context_limit": 3000, "confidence_threshold": 0.6 }`
  - Response format: 
    ```json
    {
      "response": "AI-generated answer grounded in local knowledge",
      "sources": [
        { "path": "wiki/topic.md", "snippet": "...", "relevance_score": 0.95 },
        { "path": "wiki/related.md", "snippet": "...", "relevance_score": 0.78 }
      ],
      "gaps_detected": ["specific aspect not covered"],
      "enrichment_triggered": true,
      "enrichment_status": "pending|completed",
      "confidence": 0.92
    }
    ```

- **Response Format (Standard Endpoints)**: Structured JSON with:
  - `{ results, mode, score, metadata, vectorScore?, images?, confidence }`
  - Error handling with status codes and actionable messages

### LLM Agent Interface
- **Input Contract**: Query + context (existing docs, metadata)
- **Output Contract**: Generated markdown + metadata + confidence score
- **Async Processing**: Non-blocking calls with queue support
- **Retry Logic**: Exponential backoff for failed LLM calls

### Performance & Reliability
- **Search Latency**: < 500ms for typical queries (with caching)
- **Write Operations**: Transactional, with rollback on LLM failure
- **Concurrent Requests**: Handle multiple simultaneous queries
- **Rate Limiting**: Respect LLM API limits (batch calls intelligently)
- **Logging**: Comprehensive audit trails for knowledge creation/modification

---

## Implementation Phases

### Phase 0 (MVP)
- Core read operations (keyword search + file retrieval)
- Basic write operations (create/update files)
- LLM agent integration stub
- Local markdown storage only

### Phase 1
- Vector embeddings for semantic search
- Hybrid search (keyword + vector)
- Git integration with auto-commit
- Knowledge graph visualization

### Phase 2
- LLM agent caching and optimization
- Duplicate detection and merging
- Relationship inference (auto-generate wikilinks)
- Knowledge quality scoring

### Phase 3
- Multi-project support (namespace separation)
- API authentication and access control
- Web UI for knowledge exploration
- Analytics and knowledge usage metrics

---

## Reference Architecture
This MCP should follow patterns similar to established knowledge management systems:
- **Structure**: Similar to LLM Wiki's file organization and wikilink traversal
- **API Design**: Consistent with REST conventions for CRUD + search operations
- **Error Handling**: Graceful degradation with confidence scores
- **Authentication**: Token-based when deployed in multi-user environments

---

## Open Questions for Clarification

1. **AI Response Model**: Should the MCP generate natural language responses like ChatGPT (coherent synthesis) or just return ranked document chunks? Preference: **Full synthesis with citations**

2. **Scale**: Anticipated knowledge base size (hundreds, thousands, millions of docs)?

3. **LLM Choice**: Which LLM provider/model for the agent (OpenAI, Claude, local)?

4. **Vector Embeddings**: Should we include embedding capability from phase 1, or defer to phase 2?

5. **Refresh Strategy**: How often should the MCP re-index knowledge (on-demand, scheduled, hybrid)?

6. **Conflict Resolution**: When multiple LLM calls generate similar content, how to deduplicate?

7. **Access Patterns**: Will this be used by multiple AI agents simultaneously, or single-threaded?

8. **Response Quality**: What percentage of responses should be enriched with new knowledge before returning (aggressive learning vs conservative)?

9. **Citation Format**: How should sources be presented to users (inline markdown links, separate section, metadata-only)?

10. **Hallucination Prevention**: Should the MCP refuse to answer queries with confidence < threshold, or generate responses with uncertainty disclaimers?

---

## Expected Deliverables

- [ ] Architecture Decision Record (ADR) document
- [ ] Data schema (file structure, frontmatter specification, metadata format)
- [ ] API specification (OpenAPI/Swagger definition)
- [ ] LLM agent interface specification
- [ ] Implementation roadmap with effort estimates
- [ ] Security and deployment strategy
- [ ] Monitoring and observability plan
- [ ] Code skeleton (scaffolding in preferred language)

---

## Success Criteria

- ✓ Query response time < 500ms (95th percentile)
- ✓ Zero data loss on write operations
- ✓ LLM-generated content accuracy > 90% (per manual review)
- ✓ Automatic knowledge discovery (gaps filled without manual prompt)
- ✓ Reproducible git history for all knowledge mutations
- ✓ Seamless integration with external AI agents via standard MCP protocol

---

## Complementary Implementation Notes

When implementing this architecture, also consider:

### 1. **Smart Indexing**
- Maintain in-memory cache indices for ultra-fast searches
- Lazy-load full content only when needed
- Implement bloom filters for quick "definitely not found" checks

### 2. **Deduplication Strategy**
- Use content hashing (SHA-256) to detect near-duplicates before creation
- Implement fuzzy matching for similar content
- Store similarity scores in metadata for future consolidation

### 3. **Automatic Relationship Mapping**
- MCP should suggest and auto-create wikilinks between related documents
- Build knowledge graph automatically from content analysis
- Surface orphaned documents for potential linking

### 4. **Quality Control & Confidence Scoring**
- Distinguish between manually-created vs LLM-generated content
- Implement confidence scores for all LLM outputs
- Track content provenance and evolution in metadata

### 5. **Observability & Audit Trail**
- Comprehensive logging of every search, read, and write operation
- Structured logs for analysis and improvement
- Track LLM decision reasoning for future refinement
- Monitor accuracy metrics over time

### 6. **Content Versioning**
- Beyond git history, include versioning metadata in YAML frontmatter
- Track: creation date, last modified, modification history, author/source
- Enable rollback at file level without git operations

### 7. **LLM Cost Optimization**
- Batch similar queries to reduce API calls
- Implement response caching with TTL
- Use cheaper models for gap detection, premium models for validation
- Monitor token usage and optimize prompts

### 8. **Conflict Resolution Strategy**
- Detect concurrent writes to same file
- Implement merge strategies (CRDT-inspired or operational transforms)
- Flag manual review needed for complex conflicts

---

## Reference Implementation Insights

The attached LLM Wiki SKILL reference demonstrates key patterns:

- **Hybrid Search Implementation**: Combines keyword matching with vector similarity
- **Multi-context Project Management**: Separate knowledge domains without interference
- **Error Handling Excellence**: Graceful degradation with actionable error messages
- **Authentication & Authorization**: Token-based access control suitable for production
- **Rate Limiting & Reliability**: Handles high throughput without service degradation
- **Score Interpretation**: Different scoring semantics for keyword vs vector modes

These patterns should be adapted for the MCP implementation to ensure production-grade reliability.

---

## AI-Powered Response Generation Strategy

### How the MCP Functions as an AI Assistant

The MCP transforms from a simple document retrieval system into a **knowledge-grounded AI assistant** through the following workflow:

#### 1. **Query Ingestion & Analysis**
- User submits a question or request
- MCP analyzes query intent (search, reasoning, creation, update)
- Extracts key entities and concepts for semantic matching

#### 2. **Context Retrieval** (Local-First Principle)
- Execute hybrid search (keyword + vector similarity) across markdown base
- Retrieve top 5-10 most relevant documents
- Score results by relevance, recency, and authority
- Aggregate multiple documents if query spans multiple topics
- Extract relevant snippets and build context window (2000-4000 tokens typical)

#### 3. **Confidence Assessment**
- Calculate confidence score based on:
  - Source document quality (manually-created vs LLM-generated)
  - Coverage completeness (how much of the query is addressed)
  - Source recency (is knowledge up-to-date?)
  - Consistency (do multiple sources agree?)
- If confidence < threshold: flag for enrichment

#### 4. **Response Synthesis** (AI Generation)
- Use retrieved local documents as system context
- Generate coherent, natural language response (as if written by knowledgeable assistant)
- Structure response with:
  - Main answer (grounded in local knowledge)
  - Supporting details from multiple documents
  - Explicit citations to source files
  - Confidence indicators
  - Identified knowledge gaps

#### 5. **Gap Detection & Enrichment Trigger**
- Identify aspects of query not covered by local knowledge
- Assess whether gaps are critical or optional
- For critical gaps: trigger LLM enrichment workflow
- For optional gaps: note in response that additional context available if needed

#### 6. **Post-Enrichment Re-synthesis** (Learning Loop)
- After LLM generates new markdown content
- Re-execute search to include newly-created files
- Regenerate response with comprehensive knowledge
- Return enhanced response to user
- Store decision logs for future optimization

### Key Principles

1. **Local Knowledge is Source of Truth**: All responses grounded in markdown files, never pure LLM generation
2. **Transparency**: Every claim traceable to a specific source document
3. **Continuous Learning**: Each query potentially improves knowledge base for future queries
4. **Natural Conversation**: Responses feel like talking to a knowledgeable assistant, not a document database
5. **Graceful Degradation**: Partial knowledge is better than refusal; gaps are opportunities to learn

### Example Response Flow

```
User Query: "What are the best practices for prompt engineering?"

Step 1: Search local files
→ Found: wiki/ai/prompt-engineering.md (score: 0.92)
         wiki/llm/optimization-techniques.md (score: 0.67)

Step 2: Assess confidence
→ Confidence: 0.78 (good coverage of basics, missing some advanced techniques)

Step 3: Generate response
→ Response synthesizes both documents into coherent answer
   with citations: [wiki/ai/prompt-engineering.md, wiki/llm/optimization-techniques.md]

Step 4: Detect gaps
→ Detected gap: "specific prompt templates for code generation"

Step 5: Trigger enrichment (if critical)
→ LLM creates: wiki/ai/prompt-templates-code.md

Step 6: Re-synthesize
→ Return enhanced response including new template examples
```

---

## Technology Stack Recommendations

- **Language**: Python (FastAPI) or Node.js (Express) for rapid MCP server development
- **Storage**: Filesystem with git backend (no database needed for MVP)
- **Search**: Built-in keyword search; integrate with LlamaIndex or LangChain for embeddings
- **LLM Integration**: LangChain or LlamaIndex for abstraction layer
- **Version Control**: Git with Python/Node.js bindings (GitPython, nodegit)
- **API Protocol**: Comply with MCP specification for interoperability
- **Testing**: Comprehensive unit + integration tests with mock LLM responses

---

## Deployment & Setup Strategy

### Deployment Options Overview

The MCP can be deployed in multiple configurations depending on use case, scalability needs, and integration requirements:

| Option | Architecture | Setup Complexity | Scalability | Best For |
|--------|--------------|-----------------|-------------|----------|
| **Local Development** | Standalone server on developer machine | ⭐ Very Low | Single user | Prototyping, personal knowledge base |
| **Docker Container** | Containerized MCP with volume mounts | ⭐⭐ Low | Single machine | Reproducible local setup, team development |
| **Docker Compose** | Multi-service stack (MCP + optional services) | ⭐⭐ Low | Single machine | Full stack: MCP + Redis cache + monitoring |
| **Kubernetes** | Production orchestration cluster | ⭐⭐⭐⭐ High | Highly scalable | Enterprise deployment, multi-tenancy, HA |
| **Serverless** | AWS Lambda / Google Cloud Functions | ⭐⭐⭐ Medium | Auto-scaling | Stateless queries, cost-optimized workloads |
| **Managed Cloud** | AWS AppRunner / Google Cloud Run | ⭐⭐ Low-Medium | Auto-scaling | Cloud-native without Kubernetes complexity |

---

### Option 1: Local Development Setup

**Use Case**: Prototyping, personal projects, single-user knowledge base

**Prerequisites**:
- Python 3.9+ or Node.js 18+
- Git 2.25+
- 4GB RAM minimum, 2GB disk for knowledge base

**Installation Steps**:
```bash
# 1. Clone repository
git clone <mcp-repo>
cd second-brain-agent

# 2. Create virtual environment (Python)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with:
# - LLM_API_KEY=<your-key>
# - KNOWLEDGE_BASE_PATH=./knowledge
# - SEARCH_MODE=hybrid  # keyword|vector|hybrid

# 5. Initialize knowledge base
mkdir -p knowledge/wiki
git init knowledge/

# 6. Start MCP server
python -m mcp.server  # or: npm start

# Server runs on http://localhost:8000
```

**Configuration** (`config.json`):
```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8000,
    "debug": true
  },
  "knowledge_base": {
    "root_path": "./knowledge",
    "auto_index": true,
    "index_interval_seconds": 300
  },
  "search": {
    "mode": "hybrid",
    "top_k": 5,
    "confidence_threshold": 0.6
  },
  "llm": {
    "provider": "openai",
    "model": "gpt-4-turbo",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

---

### Option 2: Docker Container Setup

**Use Case**: Team development, reproducible environments, CI/CD pipelines

**Prerequisites**:
- Docker 20.10+
- Docker Compose 2.0+ (if using compose)

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy application
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create knowledge base directory
RUN mkdir -p /data/knowledge && git init /data/knowledge

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run MCP server
CMD ["python", "-m", "mcp.server", "--host", "0.0.0.0", "--port", "8000"]
```

**Build & Run**:
```bash
# Build image
docker build -t second-brain-agent:latest .

# Run container with volume mount
docker run -d \
  --name mcp-server \
  -p 8000:8000 \
  -v $(pwd)/knowledge:/data/knowledge \
  -v $(pwd)/.env:/app/.env \
  -e LLM_API_KEY=$LLM_API_KEY \
  second-brain-agent:latest

# Check logs
docker logs -f mcp-server

# Stop container
docker stop mcp-server
```

---

### Option 3: Docker Compose Stack

**Use Case**: Full-stack deployment with caching, monitoring, and async jobs

**docker-compose.yml**:
```yaml
version: '3.9'

services:
  mcp-server:
    build: .
    container_name: second-brain-mcp
    ports:
      - "8000:8000"
    volumes:
      - ./knowledge:/data/knowledge
      - ./.env:/app/.env
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - KNOWLEDGE_BASE_PATH=/data/knowledge
      - REDIS_URL=redis://redis:6379
      - QUEUE_BROKER=redis
    depends_on:
      - redis
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: mcp-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  worker:  # Async LLM enrichment jobs
    build: .
    container_name: mcp-worker
    command: python -m mcp.worker
    volumes:
      - ./knowledge:/data/knowledge
      - ./.env:/app/.env
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - KNOWLEDGE_BASE_PATH=/data/knowledge
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    networks:
      - mcp-network

  prometheus:  # Monitoring (optional)
    image: prom/prometheus:latest
    container_name: mcp-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    networks:
      - mcp-network

volumes:
  redis-data:

networks:
  mcp-network:
    driver: bridge
```

**Startup**:
```bash
# Create .env file
cp .env.example .env
# Edit with your configuration

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f mcp-server

# Stop all services
docker-compose down
```

---

### Option 4: Kubernetes Deployment

**Use Case**: Production environment, multi-tenancy, high availability, auto-scaling

**Prerequisites**:
- Kubernetes 1.24+
- kubectl configured
- Container registry (Docker Hub, ECR, GCR)

**k8s/mcp-deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: second-brain-mcp
  namespace: knowledge-base
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: your-registry/second-brain-agent:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: LLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-credentials
              key: api-key
        - name: KNOWLEDGE_BASE_PATH
          value: /data/knowledge
        - name: REDIS_URL
          value: redis://redis-service:6379
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: knowledge-volume
          mountPath: /data/knowledge
      volumes:
      - name: knowledge-volume
        persistentVolumeClaim:
          claimName: knowledge-base-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-service
  namespace: knowledge-base
spec:
  type: LoadBalancer
  selector:
    app: mcp-server
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: knowledge-base-pvc
  namespace: knowledge-base
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
```

**Deploy**:
```bash
# Create namespace
kubectl create namespace knowledge-base

# Create secrets
kubectl create secret generic llm-credentials \
  --from-literal=api-key=$LLM_API_KEY \
  -n knowledge-base

# Deploy
kubectl apply -f k8s/mcp-deployment.yaml

# Monitor
kubectl get pods -n knowledge-base
kubectl logs -f deployment/second-brain-mcp -n knowledge-base

# Scale
kubectl scale deployment second-brain-mcp --replicas=5 -n knowledge-base
```

---

### Option 5: Serverless (AWS Lambda / Google Cloud Functions)

**Use Case**: Cost-optimized, variable workloads, minimal infrastructure management

**Constraints**:
- Stateless design (no local file persistence between invocations)
- Must use cloud storage (S3, Cloud Storage) for knowledge base
- Execution timeout: 900s (15 minutes) max
- Cold start latency acceptable

**AWS Lambda Deployment**:

```python
# lambda_handler.py
import json
import os
from mcp.api import MCPServer

# Initialize at module level (reused across invocations)
mcp = MCPServer(
    knowledge_base_path=os.getenv('KNOWLEDGE_BASE_S3'),
    cache_ttl=300
)

def handler(event, context):
    """
    Lambda event structure:
    {
        "httpMethod": "POST",
        "path": "/query",
        "body": {"query": "..."}
    }
    """
    
    try:
        if event['httpMethod'] == 'POST':
            path = event['path']
            body = json.loads(event.get('body', '{}'))
            
            if path == '/query':
                response = mcp.query(body['query'])
            elif path == '/search':
                response = mcp.search(body['query'])
            elif path == '/enrich':
                response = mcp.enrich(body)
            else:
                return error_response(404, "Not found")
            
            return success_response(response)
        else:
            return error_response(405, "Method not allowed")
            
    except Exception as e:
        return error_response(500, str(e))

def success_response(data):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data)
    }

def error_response(code, message):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message})
    }
```

**Deploy with SAM**:
```bash
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  MCPFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.11
      Handler: lambda_handler.handler
      CodeUri: .
      Timeout: 900
      MemorySize: 1024
      Environment:
        Variables:
          KNOWLEDGE_BASE_S3: s3://knowledge-base-bucket/wiki
          LLM_API_KEY: !Ref LLMApiKeyParameter
      Policies:
        - S3CrudPolicy:
            BucketName: knowledge-base-bucket
      Events:
        ApiEvent:
          Type: Api
          Properties:
            RestApiId: !Ref MCPApi
            Path: /{proxy+}
            Method: ANY

  MCPApi:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: second-brain-mcp-api

Parameters:
  LLMApiKeyParameter:
    Type: String
    NoEcho: true
```

**Deploy**:
```bash
sam build
sam deploy --guided
```

---

### Option 6: Managed Cloud (AWS AppRunner / Google Cloud Run)

**Use Case**: Cloud-native deployment without Kubernetes complexity

**Google Cloud Run**:

```bash
# 1. Build and push container
gcloud builds submit --tag gcr.io/PROJECT_ID/second-brain-mcp

# 2. Deploy
gcloud run deploy second-brain-mcp \
  --image gcr.io/PROJECT_ID/second-brain-mcp \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars=KNOWLEDGE_BASE_PATH=/data/knowledge,LLM_API_KEY=$LLM_API_KEY \
  --allow-unauthenticated

# 3. Set up Cloud Storage for knowledge base (backup/sync)
gsutil cp -r ./knowledge gs://knowledge-base-backup/
```

**AWS AppRunner**:

```bash
# 1. Create AppRunner service
aws apprunner create-service \
  --service-name second-brain-mcp \
  --source-configuration \
    RepositoryType=GITHUB,ImageRepository=PROJECT_ID/second-brain-mcp,ImageRepositoryType=ECR \
  --instance-configuration \
    InstanceRoleArn=arn:aws:iam::ACCOUNT_ID:role/apprunner-role \
  --auto-deployments-config AutoDeploymentsEnabled=true

# 2. Configure auto-deployments
aws apprunner update-service \
  --service-arn arn:aws:apprunner:region:ACCOUNT_ID:service/second-brain-mcp \
  --auto-deployments-config AutoDeploymentsEnabled=true
```

---

## Deployment Comparison & Recommendations

### Decision Matrix

```
Small Team / Prototyping?        → Local Development or Docker
Production Single Machine?        → Docker Compose
Enterprise / Multi-tenant?        → Kubernetes
Cost-optimized Bursty Traffic?   → Serverless (Lambda/Cloud Functions)
Managed Cloud Preference?         → AppRunner / Cloud Run
```

### Setup Summary by Complexity

**Minimal Setup** (< 10 minutes):
- Local Development: bash + git
- Docker Container: docker run

**Standard Setup** (20-30 minutes):
- Docker Compose: multi-service orchestration
- Managed Cloud: AppRunner / Cloud Run

**Advanced Setup** (1-2 hours):
- Kubernetes: full HA setup
- Serverless: S3 integration, IAM roles

---

## Common Configuration Across All Deployments

### Environment Variables
```bash
# Required
LLM_API_KEY=                    # OpenAI / Claude / etc.
KNOWLEDGE_BASE_PATH=           # /path/to/knowledge or s3://bucket/path
SEARCH_MODE=hybrid              # keyword|vector|hybrid

# Optional
LOG_LEVEL=info                  # debug|info|warning|error
CACHE_TTL_SECONDS=300
REDIS_URL=                      # redis://localhost:6379 (for cache)
GIT_AUTO_COMMIT=true            # Enable auto-commit
VECTOR_EMBEDDING_MODEL=text-embedding-3-small
```

### Health Check Endpoints
- `GET /health` — Server status (always available)
- `GET /ready` — Ready to handle requests (checks dependencies)
- `GET /metrics` — Prometheus metrics (optional)

### Monitoring & Observability
- Logs: Structured JSON format (ECS-compatible)
- Metrics: Prometheus-compatible endpoint
- Tracing: OpenTelemetry support (production deployments)

---

## Migration Path

**Recommended progression for growing teams**:

1. Start with **Local Development** for prototyping
2. Move to **Docker Container** when collaborating
3. Upgrade to **Docker Compose** for full-stack features
4. Scale to **Kubernetes** when approaching 100+ concurrent users
5. Consider **Serverless** for variable-load scenarios

Each step is backward-compatible; knowledge base remains filesystem-based until Kubernetes deployment (where it moves to persistent volumes).
