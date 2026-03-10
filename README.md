# DevOps Project

A production-ready FastAPI application with full DevOps pipeline including Docker, Kubernetes, CI/CD, Terraform, and monitoring.

## Architecture

- **Application**: FastAPI (Python) with PostgreSQL
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes (EKS) with Ingress + HPA + PDB
- **CI/CD**: GitHub Actions (test, build, GitOps deploy via ArgoCD)
- **GitOps**: ArgoCD for automated K8s deployments
- **IaC**: Terraform (AWS VPC, EKS, RDS, ALB, NAT Gateway)
- **Monitoring**: Prometheus + Grafana + cAdvisor
- **Logging**: Loki + Promtail (centralized, viewable in Grafana)
- **Reverse Proxy**: Nginx
- **Security**: NetworkPolicy, private subnets, Security Groups

### Production Architecture Diagram

```mermaid
graph TB
    subgraph internet [Internet]
        User[Users]
        GitHub[GitHub Repo]
        DockerHub[Docker Hub]
    end

    subgraph aws [AWS Cloud - ap-south-1]
        Route53[Route 53 DNS]
        ALB["ALB (Load Balancer)"]

        subgraph vpc [VPC 10.0.0.0/16]
            subgraph publicSubnets [Public Subnets - 2 AZs]
                NAT[NAT Gateway]
                Bastion[Bastion Host]
            end

            subgraph privateSubnets [Private Subnets - 2 AZs]
                subgraph eks [EKS Cluster]
                    Ingress[Nginx Ingress]
                    Pods["FastAPI (3-10 pods)"]
                    Monitoring["Prometheus + Grafana + Loki"]
                    ArgoCD[ArgoCD]
                end
                RDS["RDS PostgreSQL (Multi-AZ)"]
            end
        end
    end

    User --> Route53 --> ALB --> Ingress --> Pods --> RDS
    ArgoCD --> GitHub
    GitHub --> DockerHub
```

### CI/CD Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant GA as GitHub Actions
    participant DH as Docker Hub
    participant Argo as ArgoCD
    participant EKS as EKS Cluster

    Dev->>GH: Push to main
    GH->>GA: Trigger pipeline
    GA->>GA: Test + Lint
    GA->>DH: Build and push image
    GA->>GH: Update image tag in k8s/deployment.yml
    GH-->>Argo: Detects change
    Argo->>EKS: Sync deployment
    EKS->>EKS: Rolling update
```

> Full architecture details: [docs/architecture.md](docs/architecture.md)

## Quick Start (Docker Compose)

1. Clone the repository:
   ```bash
   git clone https://github.com/imperfect0007/devopsproject.git
   cd devopsproject
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Update the `.env` file with your credentials.

4. Start all services:
   ```bash
   docker compose up -d
   ```

5. Access the services:
   - App (via Nginx): http://localhost:8080
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000
   - Loki (log API): http://localhost:3100
   - cAdvisor: http://localhost:8081

## API Endpoints

| Endpoint     | Description                    |
|-------------|--------------------------------|
| `GET /`     | App status and hostname        |
| `GET /health` | Health check                 |
| `GET /db-check` | Database connectivity check |
| `GET /metrics` | Prometheus metrics           |

## Kubernetes Deployment

### Option 1: Manual Deployment (without ArgoCD)

1. Create the database secret:
   ```bash
   kubectl create secret generic fastapi-secrets \
     --from-literal=database-url="postgresql://user:password@db-host:5432/tasks"
   ```

2. Apply the manifests:
   ```bash
   kubectl apply -f k8s/
   ```

### Option 2: GitOps with ArgoCD (Recommended)

ArgoCD continuously watches your Git repo and automatically syncs Kubernetes manifests to the cluster. Any change you push to the `k8s/` folder in `main` branch gets deployed automatically.

#### Prerequisites

- A running Kubernetes cluster (EKS, Minikube, k3s, etc.)
- `kubectl` configured and connected to the cluster

#### Step 1: Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Wait for all ArgoCD pods to be ready:

```bash
kubectl wait --for=condition=ready pod --all -n argocd --timeout=300s
```

#### Step 2: Access the ArgoCD UI

Expose the ArgoCD server:

```bash
kubectl port-forward svc/argocd-server -n argocd 8443:443
```

Open https://localhost:8443 in your browser.

Get the initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Login with username `admin` and the password from above.

#### Step 3: Create the Database Secret

ArgoCD manages the `k8s/` manifests, but secrets should be created separately:

```bash
kubectl create secret generic fastapi-secrets \
  --from-literal=database-url="postgresql://user:password@db-host:5432/tasks"
```

#### Step 4: Register the Application with ArgoCD

```bash
kubectl apply -f argocd/application.yml
```

This tells ArgoCD to:
- Watch the `k8s/` path in `https://github.com/imperfect0007/devopsproject`
- Deploy manifests to the `default` namespace
- Auto-sync on every git push (`automated: true`)
- Auto-prune deleted resources (`prune: true`)
- Auto-heal manual changes (`selfHeal: true`)

#### Step 5: Verify the Deployment

Check the app status in ArgoCD:

```bash
kubectl get applications -n argocd
```

Or use the ArgoCD CLI:

```bash
kubectl -n argocd exec -it deploy/argocd-server -- argocd app get fastapi-app
```

#### How It Works After Setup

1. You push code changes to `main` branch
2. GitHub Actions builds a new Docker image and pushes it to Docker Hub
3. You update the image tag in `k8s/deployment.yml` and push
4. ArgoCD detects the change in Git and automatically syncs the new deployment
5. Kubernetes rolls out the updated pods with zero downtime

> **Important**: Do NOT run `kubectl apply -f k8s/` manually when using ArgoCD. ArgoCD's `selfHeal` will revert any manual changes to match what is in Git.

#### Uninstall ArgoCD

```bash
kubectl delete -f argocd/application.yml
kubectl delete namespace argocd
```

## Logging

This project uses a full centralized logging stack. All logs flow into **Grafana** where you can search, filter, and build dashboards.

### How It Works

```
App (JSON stdout) ──┐
Nginx (JSON logs) ──┤──> Promtail ──> Loki ──> Grafana
Postgres (stdout) ──┘
```

| Component  | Role                                      | Port |
|-----------|-------------------------------------------|------|
| **Loki**  | Log aggregation and storage (like Prometheus, but for logs) | 3100 |
| **Promtail** | Log collector -- reads logs and ships them to Loki | 9080 |
| **Grafana** | UI to query and visualize logs             | 3000 |

### Application Logs

The FastAPI app outputs structured JSON logs to stdout:

```json
{"timestamp": "2026-03-09 12:00:00", "level": "INFO", "logger": "app", "message": "request completed"}
```

Every HTTP request (except `/health` and `/metrics`) is logged with method, path, status code, duration, and client IP.

### Nginx Logs

Nginx writes JSON-formatted access logs to `/var/log/nginx/access.log`:

```json
{"timestamp": "2026-03-09T12:00:00+00:00", "remote_addr": "172.18.0.1", "method": "GET", "uri": "/", "status": 200, "request_time": 0.003}
```

### Viewing Logs in Grafana

1. Open Grafana at http://localhost:3000 (default login: `admin` / `admin`)
2. Go to **Explore** (compass icon in the sidebar)
3. Select **Loki** as the data source
4. Run queries:

   - All backend logs:
     ```
     {job="docker"} |= "backend"
     ```

   - All Nginx access logs:
     ```
     {job="nginx"}
     ```

   - Filter errors only:
     ```
     {job="docker"} |= "ERROR"
     ```

   - Nginx 5xx errors:
     ```
     {job="nginx"} | json | status >= 500
     ```

### Docker Log Rotation

All services have log rotation configured to prevent disk from filling up:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"   # rotate after 10MB
    max-file: "3"     # keep 3 rotated files
```

### Viewing Raw Docker Logs

You can also view logs directly with Docker without Grafana:

```bash
# All backend logs
docker compose logs backend -f

# All Nginx logs
docker compose logs nginx -f

# All services
docker compose logs -f
```

## Terraform (AWS Infrastructure)

Terraform provisions the full production AWS stack: VPC, EKS, RDS, ALB, NAT Gateway, and Bastion host.

1. Copy the example variables file:
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your values (key pair, SSH CIDR, DB password).

3. Initialize and apply:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

4. Configure kubectl to use the new EKS cluster:
   ```bash
   aws eks update-kubeconfig --name devops-project --region ap-south-1
   ```

### Terraform Files

| File | Resources |
|------|-----------|
| `main.tf` | Provider config, Bastion host |
| `vpc.tf` | VPC, subnets (public + private), IGW, NAT Gateway, route tables |
| `eks.tf` | EKS cluster, node group, IAM roles |
| `rds.tf` | PostgreSQL RDS (Multi-AZ), DB subnet group, security group |
| `alb.tf` | Application Load Balancer, target group, listener |
| `backend.tf` | S3 remote state config (commented, enable after creating bucket) |
| `variables.tf` | All input variables |
| `outputs.tf` | Cluster endpoint, RDS endpoint, ALB DNS, kubectl command |

## CI/CD Pipeline

The GitHub Actions pipeline runs on push to `main` with three stages:

1. **Test** -- Lint (ruff) and unit tests (pytest)
2. **Build & Push** -- Docker image tagged with git SHA, pushed to Docker Hub
3. **Deploy** -- Updates image tag in `k8s/deployment.yml` and pushes to Git. ArgoCD detects the change and syncs to EKS automatically.

### Required GitHub Secrets

| Secret              | Description                |
|--------------------|----------------------------|
| `DOCKERHUB_USERNAME` | Docker Hub username        |
| `DOCKERHUB_PASSWORD` | Docker Hub password/token  |

## Project Structure

```
.
├── app/                        # FastAPI application
│   ├── main.py
│   └── requirements.txt
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yml
│   ├── configmap.yml
│   ├── deployment.yml
│   ├── service.yml
│   ├── ingress.yaml
│   ├── hpa.yml                 # Horizontal Pod Autoscaler
│   ├── pdb.yml                 # Pod Disruption Budget
│   └── networkpolicy.yml       # Network segmentation
├── terraform/                  # AWS infrastructure (IaC)
│   ├── main.tf                 # Provider + Bastion
│   ├── vpc.tf                  # VPC, subnets, NAT, IGW
│   ├── eks.tf                  # EKS cluster + node group
│   ├── rds.tf                  # PostgreSQL Multi-AZ
│   ├── alb.tf                  # Application Load Balancer
│   ├── backend.tf              # S3 remote state
│   ├── variables.tf
│   └── outputs.tf
├── monitoring/                 # Monitoring & logging configs
│   ├── prometheus.yml
│   ├── promtail-config.yml
│   ├── grafana-datasources.yml
│   └── grafana-deployment.yml
├── argocd/                     # GitOps
│   └── application.yml
├── docs/                       # Documentation
│   └── architecture.md         # Production HLD
├── .github/workflows/          # CI/CD
│   └── ci.yml
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── .env                        # Local secrets (not committed)
```
