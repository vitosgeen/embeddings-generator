# Security Policy

## Overview

This project follows security best practices while balancing dependency compatibility for machine learning workloads.

## Known Security Issues

### Current Status
- **5 vulnerabilities** detected in dependencies
- **Mitigation strategy** implemented via `.safety-policy.yml`
- **Regular monitoring** for compatible updates

### Vulnerability Details

#### PyTorch (torch==2.4.1)
- **CVE-2025-32434, CVE-2025-3730, CVE-2025-2953**
- **Impact**: Various DoS vulnerabilities
- **Mitigation**: Monitoring for updates compatible with sentence-transformers
- **Risk Level**: Low (internal service, controlled environment)

#### Starlette (0.41.3)
- **CVE-2025-54121** 
- **Impact**: DoS via large request handling
- **Mitigation**: Rate limiting, input validation (implemented in FastAPI layer)
- **Risk Level**: Medium (will update when FastAPI supports newer versions)

#### Protobuf (5.27.3)
- **CVE-2025-4565**
- **Impact**: DoS via unbounded recursion
- **Mitigation**: Input validation, request size limits
- **Risk Level**: Low (controlled gRPC usage)

## Security Controls

### Application Level
1. **Input Validation**: All API endpoints validate input size and format
2. **Rate Limiting**: Implemented at reverse proxy level (recommended)
3. **Request Timeouts**: Configured in FastAPI and gRPC services
4. **Resource Limits**: Docker container resource constraints

### Infrastructure Level
1. **Network Isolation**: Service runs in controlled environment
2. **Authentication**: Token-based auth (when deployed)
3. **Monitoring**: Application and security logging
4. **Updates**: Automated dependency scanning via CI/CD

### CI/CD Security
1. **Dependency Scanning**: Safety + Bandit in every build
2. **Secret Management**: GitHub Secrets for sensitive data
3. **Image Scanning**: Docker images scanned for vulnerabilities
4. **Branch Protection**: Required status checks and reviews

## Dependency Management Strategy

### Regular Updates
- **Monthly**: Review and test dependency updates
- **Weekly**: Check for security patches in primary dependencies  
- **Daily**: Automated scanning via CI/CD pipeline

### Compatibility Testing
- **ML Dependencies**: PyTorch, sentence-transformers compatibility matrix
- **API Dependencies**: FastAPI, Starlette version alignment
- **Protocol Dependencies**: gRPC, protobuf version synchronization

### Risk Assessment Matrix
```
High Risk: Core API vulnerabilities (FastAPI, uvicorn)
Medium Risk: Framework vulnerabilities (PyTorch, Starlette) 
Low Risk: Tool vulnerabilities (protobuf, testing deps)
```

## Incident Response

### Vulnerability Discovery
1. **Immediate**: Review impact assessment
2. **24 Hours**: Implement workarounds/mitigations
3. **1 Week**: Test and deploy dependency updates
4. **Follow-up**: Update security policy and documentation

### Security Contacts
- **Primary**: Development team lead
- **Security**: Infrastructure team
- **Escalation**: Security officer

## Compliance

### Standards
- **OWASP**: Top 10 web application security risks
- **NIST**: Cybersecurity framework alignment
- **Industry**: ML/AI security best practices

### Auditing
- **Dependencies**: Monthly security audit
- **Code**: Static analysis via bandit
- **Infrastructure**: Container and deployment security review

## References
- [Safety Documentation](https://pyup.io/safety/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [gRPC Security](https://grpc.io/docs/guides/auth/)
- [Docker Security](https://docs.docker.com/engine/security/)