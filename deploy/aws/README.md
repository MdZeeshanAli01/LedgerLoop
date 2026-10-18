# AWS deployment bundle

This folder contains secret-free deployment files for Hisaabset:

- `hisaabset-ses-task-policy.json`: least-privilege SES send policy for the
  ECS task role.
- `hisaabset-task-definition.template.json`: Fargate task definition template.
- `deploy.ps1`: builds and pushes the Docker image to ECR and renders a task
  definition for the selected AWS account/region.

## Prerequisites

Install and authenticate:

- Docker Desktop
- AWS CLI
- An AWS identity with ECR push and ECS deployment permissions

Verify the AWS identity:

```powershell
aws sts get-caller-identity
```

The script never asks for or stores AWS secrets. The running container should
use an ECS task role, not root credentials or access keys.

## Build and push

From the repository root:

```powershell
.\deploy\aws\deploy.ps1 -Region ap-south-1 -Tag v1
```

The default image environment keeps email test mode enabled. To render a live
email task definition explicitly:

```powershell
.\deploy\aws\deploy.ps1 -Region ap-south-1 -Tag v1 -LiveEmail
```

Only use `-LiveEmail` after:

1. SES sender identity is verified.
2. Test recipient is verified or SES production access is approved.
3. The ECS task role has the policy in `hisaabset-ses-task-policy.json`.
4. The application has passed a test-mode review.
5. The first live recipient is controlled by the finance team.

## Container smoke test

```powershell
docker build -t hisaabset:local .
docker run --rm -p 8501:8501 `
  -e AWS_REGION=ap-south-1 `
  -e HISAABSET_EMAIL_SENDER=unnamedinsect424@gmail.com `
  -e HISAABSET_EMAIL_TEST_MODE=true `
  hisaabset:local
```

Open `http://localhost:8501` and verify:

```text
http://localhost:8501/_stcore/health
```

## ECS values

Use these values when creating the Fargate service:

```text
Cluster: hisaabset-cluster
Service: hisaabset-service
Container: hisaabset
Container port: 8501
Health check: /_stcore/health
Log group: /ecs/hisaabset
Task CPU: 512
Task memory: 1024 MiB
```

The task definition template expects these IAM roles:

```text
Execution role: ecsTaskExecutionRole
Task role: HisaabsetEcsTaskRole
```

The task role should have only the SES send policy, restricted to the verified
sender address. Do not put root access keys in Docker, ECS environment
variables, GitHub, or this repository.
