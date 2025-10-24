# CI/CD Setup Guide

## Overview

This project is configured with a comprehensive CI/CD pipeline using GitHub Actions. The pipeline includes automated testing, code quality checks, security scanning, Docker image building, and deployment preparation.

## Prerequisites

### 1. GitHub Repository Setup
```bash
# Initialize git repository (already done)
git init
git branch -m main

# Configure git user (update with your details)
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 2. Required GitHub Secrets

Set up the following secrets in your GitHub repository settings:

- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token (not password!)

### 3. Codecov Setup (Optional but Recommended)

For coverage reporting and tracking:

1. **Sign up**: Go to [codecov.io](https://codecov.io) and sign in with your GitHub account
2. **Add Repository**: Add your repository to Codecov
3. **Get Upload Token**: Copy the upload token from your Codecov repository settings
4. **Add GitHub Secret**: Add `CODECOV_TOKEN` secret in your GitHub repository settings
5. **Badge**: Add a coverage badge to your README.md:
   ```markdown
   [![codecov](https://codecov.io/gh/yourusername/embeddings-generator/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/embeddings-generator)
   ```

> **Note**: Without the CODECOV_TOKEN, uploads may fail due to rate limiting. The CI will continue to work, but coverage reports won't be uploaded.

## Pipeline Stages

### 1. **Testing** (`test` job)
- Runs on Python 3.8, 3.9, 3.10, and 3.11
- Executes unit and integration tests
- Generates coverage reports
- Uploads coverage to Codecov

### 2. **Security Scanning** (`security-scan` job)
- Checks dependencies for known vulnerabilities with Safety
- Scans code for security issues with Bandit
- Runs in parallel with testing

### 3. **Docker Build** (`docker-build` job)
- Only runs on `main` branch after tests pass
- Builds Docker image with BuildKit
- Pushes to Docker Hub with `latest` and commit SHA tags
- Uses GitHub Actions cache for faster builds

### 4. **Deployment** (`deploy` job)
- Only runs on `main` branch after Docker build
- Currently contains placeholder deployment logic
- Configure based on your deployment target

## Local Development Workflow

### Code Quality Checks
```bash
# Format code
make format

# Check formatting (CI-friendly)
make format-check

# Run linters
make lint

# Security checks
make security

# All quality checks
make quality
```

### Testing
```bash
# Run all tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Coverage report
make test-coverage

# Watch mode for development
make test-watch
```

## GitHub Actions Workflow

The workflow is triggered on:
- Push to `main` or `develop` branches
- Pull requests to `main` branch

### Workflow File Location
`.github/workflows/ci-cd.yml`

### Branch Protection

Recommended branch protection rules for `main`:
1. Require pull request reviews
2. Require status checks to pass:
   - `test (3.8)`
   - `test (3.9)`
   - `test (3.10)`
   - `test (3.11)`
   - `security-scan`
3. Require branches to be up to date
4. Restrict pushes to protected branch

## Configuration Files

### Code Quality Tools
- **Black**: Code formatter (`.pyproject.toml`)
- **isort**: Import sorter (`.pyproject.toml`)
- **flake8**: Linter (uses default config)
- **Bandit**: Security linter (`.pyproject.toml`)
- **Safety**: Dependency vulnerability scanner

### Testing Configuration
- **pytest**: Test runner (`.pyproject.toml`)
- **Coverage**: Coverage reporting (`.pyproject.toml`)
- Minimum coverage threshold: 80%

### Docker Configuration
- **Dockerfile**: Multi-stage build for production
- **docker-compose.yml**: Local development environment

## Deployment Configuration

### Current Setup
The deployment stage is currently a placeholder. Configure it based on your target platform:

#### Option 1: Kubernetes
```yaml
- name: Deploy to Kubernetes
  run: |
    kubectl set image deployment/embeddings-api embeddings-api=${{ secrets.DOCKERHUB_USERNAME }}/embeddings-generator:${{ github.sha }}
```

#### Option 2: Docker Compose on Server
```yaml
- name: Deploy via SSH
  run: |
    ssh user@server "cd /app && docker-compose pull && docker-compose up -d"
```

#### Option 3: Cloud Platforms
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances

### Environment Variables
Set these in your deployment environment:
- `PORT`: Service port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

## Monitoring and Alerts

### Health Checks
The application exposes health check endpoints:
- REST: `GET /health`
- gRPC: Custom health check service

### Recommended Monitoring
- Application metrics (Prometheus/Grafana)
- Log aggregation (ELK Stack/Fluentd)
- Error tracking (Sentry)
- Uptime monitoring (Pingdom/StatusPage)

## Troubleshooting

### Common Issues

#### 1. Test Failures in CI
```bash
# Run tests locally to debug
make test-coverage
# Check coverage report in htmlcov/index.html
```

#### 2. Docker Build Failures
```bash
# Test Docker build locally
docker build -t embeddings-test .
docker run --rm embeddings-test python -c "import app; print('OK')"
```

#### 3. Security Scan Failures
```bash
# Run security checks locally
make security
# Fix reported vulnerabilities before pushing
```

#### 4. Code Quality Issues
```bash
# Auto-fix formatting issues
make format
# Check what linting issues remain
make lint
```

### Getting Help

1. Check GitHub Actions logs for detailed error messages
2. Run the failing command locally with the same Python version
3. Ensure all dependencies in `requirements.txt` are up to date
4. Verify environment variables and secrets are correctly configured

## Performance Optimization

### CI/CD Speed Improvements
- Dependencies are cached between runs
- Docker layers are cached with GitHub Actions cache
- Tests run in parallel across multiple Python versions
- Matrix builds allow early detection of version-specific issues

### Resource Usage
- Each job runs on fresh Ubuntu runners
- Parallel execution minimizes total pipeline time
- Docker BuildKit improves build performance
- Coverage reports are generated efficiently

## Security Considerations

### Dependency Management
- `safety` checks for known vulnerabilities
- Regular dependency updates via Dependabot (configure separately)
- Pinned versions in `requirements.txt` for reproducibility

### Code Security
- `bandit` scans for common security issues
- No secrets stored in code (use GitHub Secrets)
- Docker images use non-root user
- Multi-stage builds minimize attack surface

### Access Control
- GitHub repository access controls
- Docker Hub token-based authentication
- Deployment environment isolation
- Branch protection prevents direct pushes to main