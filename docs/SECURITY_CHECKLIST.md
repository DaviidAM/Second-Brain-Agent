# Security Checklist

## API Key Management
- [ ] Store API keys in environment variables, not in code
- [ ] Use secrets management (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault)
- [ ] Rotate API keys periodically
- [ ] Never commit API keys to version control

## Network Security
- [ ] Use TLS for all external connections
- [ ] Implement rate limiting to prevent abuse
- [ ] Configure firewall rules for Kubernetes/Docker
- [ ] Use network policies in Kubernetes

## Container Security
- [ ] Use non-root user in Docker container
- [ ] Scan images for vulnerabilities (Trivy, Snyk)
- [ ] Use minimal base images
- [ ] Enable read-only file system where possible
- [ ] Don't run containers as privileged

## Data Security
- [ ] Enable encryption at rest for wiki storage
- [ ] Use secure storage for index files
- [ ] Implement backup strategy
- [ ] Sanitize sensitive data in logs

## Access Control
- [ ] Implement authentication for API endpoints
- [ ] Use role-based access control (RBAC)
- [ ] Limit permissions to minimum required
- [ ] Audit access logs regularly

## Monitoring
- [ ] Enable structured logging
- [ ] Set up alerts for security events
- [ ] Monitor failed authentication attempts
- [ ] Track API key usage

## Compliance
- [ ] Document data handling procedures
- [ ] Implement audit trail
- [ ] Regular security reviews
- [ ] Incident response plan
