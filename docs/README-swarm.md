# Hyper-Swarm PoC

A distributed system architecture implementing a swarm of specialized AI cells for collaborative task execution.

## Architecture Overview

Hyper-Swarm consists of four specialized cell types that work together:

- **Planner Cell**: Orchestrates task decomposition and execution planning
- **Curator Cell**: Manages knowledge indexing and retrieval using vector databases
- **Archivist Cell**: Handles long-term storage and artifact management
- **Watcher Cell**: Monitors system health, metrics, and provides observability

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Kubernetes (kind/minikube/k3s)
- kubectl
- Knative CLI (optional)

### Local Development Setup

1. **Start Infrastructure Services**
   ```bash
   cd compose
   docker-compose up -d
   ```

   This starts:
   - MinIO (S3-compatible storage) on ports 9000/9001
   - Milvus (vector database) on port 19530
   - Grafana (monitoring) on port 3000
   - Prometheus on port 9090
   - Redis on port 6379
   - NATS Streaming on port 4222

2. **Create kind Cluster**
   ```bash
   kind create cluster --config infra/kind-dev/kind.yaml
   ```

3. **Install Knative Serving**
   ```bash
   # Install Knative Serving CRDs
   kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-crds.yaml
   
   # Install Knative Serving core
   kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-core.yaml
   
   # Install networking layer (Kourier)
   kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.12.0/kourier.yaml
   
   # Configure Knative to use Kourier
   kubectl patch configmap/config-network \
     --namespace knative-serving \
     --type merge \
     --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'
   ```

4. **Deploy Base Infrastructure**
   ```bash
   kubectl apply -f infra/k8s/base/broker.yaml
   ```

5. **Deploy Sample Cells**
   ```bash
   kubectl apply -f infra/k8s/overlays/dev/sample-ksvc.yaml
   ```

## Cell Types

### Planner Cell
- **Purpose**: Task decomposition and orchestration
- **Responsibilities**:
  - Parse high-level requests
  - Create execution plans
  - Distribute tasks to appropriate cells
  - Monitor task progress

### Curator Cell
- **Purpose**: Knowledge management and retrieval
- **Responsibilities**:
  - Index documents and embeddings
  - Perform semantic search
  - Manage vector database operations
  - Cache frequently accessed data

### Archivist Cell
- **Purpose**: Long-term storage and artifact management
- **Responsibilities**:
  - Store generated artifacts
  - Manage object storage
  - Handle data retention policies
  - Provide artifact retrieval

### Watcher Cell
- **Purpose**: System observability and health monitoring
- **Responsibilities**:
  - Collect metrics from all cells
  - Monitor system health
  - Alert on anomalies
  - Provide debugging insights

## Communication Patterns

Cells communicate through:
1. **NATS Streaming**: Asynchronous message passing
2. **Redis**: Shared state and caching
3. **HTTP/gRPC**: Direct cell-to-cell communication

## Development Workflow

1. **Cell Development**
   ```bash
   cd cells/planner
   # Implement cell logic
   # Build container: docker build -t ghcr.io/hyper-swarm/planner-cell:latest .
   ```

2. **Local Testing**
   ```bash
   # Run cell locally with compose services
   NATS_URL=nats://localhost:4222 \
   REDIS_URL=redis://localhost:6379 \
   go run main.go
   ```

3. **Deploy to Kubernetes**
   ```bash
   kubectl apply -f infra/k8s/overlays/dev/sample-ksvc.yaml
   ```

## Monitoring

Access Grafana at http://localhost:3000 (admin/admin) to view:
- Cell performance metrics
- Message queue statistics
- Resource utilization
- Error rates and latency

## Storage Systems

- **MinIO**: Object storage for artifacts, models, and datasets
  - Console: http://localhost:9001 (minioadmin/minioadmin)
- **Milvus**: Vector database for embeddings
  - Endpoint: localhost:19530
- **Redis**: Cache and shared state
  - Endpoint: localhost:6379

## Scaling

Knative automatically scales cells based on:
- Request volume
- CPU/Memory utilization
- Custom metrics

Configure scaling in the Knative Service annotations:
```yaml
annotations:
  autoscaling.knative.dev/minScale: "0"
  autoscaling.knative.dev/maxScale: "10"
  autoscaling.knative.dev/target: "10"
```

## Troubleshooting

1. **Check Cell Status**
   ```bash
   kubectl get ksvc -n hyper-swarm
   ```

2. **View Cell Logs**
   ```bash
   kubectl logs -n hyper-swarm -l cell-type=planner
   ```

3. **Check Message Broker**
   ```bash
   kubectl logs -n hyper-swarm deployment/nats-streaming
   ```

4. **Access Metrics**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000

## Next Steps

1. Implement cell business logic
2. Define message schemas
3. Create integration tests
4. Set up CI/CD pipelines
5. Configure production overlays
6. Implement security policies