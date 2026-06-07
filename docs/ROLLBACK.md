# Rollback Strategy

## Emergency Rollback Procedures

### Docker Rollback

```bash
# List previous images
docker images | grep mcp-server

# Rollback to previous version
docker run mcp-server:<previous-tag>

# Or use docker-compose
docker-compose down
docker-compose up mcp-server:<previous-tag>
```

### Kubernetes Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/mcp-server

# Check rollout status
kubectl rollout status deployment/mcp-server

# Rollback to specific revision
kubectl rollout undo deployment/mcp-server --to-revision=3
```

### Database/Index Rollback

If index corruption occurs:

```bash
# Restore from backup
tar -xzf backup-20240101.tar.gz

# Rebuild index
python -m src.mcp.indexing --rebuild
```

## Configuration Rollback

```bash
# Revert environment variables
source old-config.sh

# Restart service
kubectl rollout restart deployment/mcp-server
```

## Emergency Contacts

| Role | Contact | Response Time |
|------|---------|---------------|
| On-call Engineer | TODO | 15 min |
| DevOps Lead | TODO | 30 min |
| Security Team | TODO | 1 hour |

## Post-Incident

1. Document incident timeline
2. Analyze root cause
3. Update monitoring/alerting
4. Test rollback procedure
5. Update runbook if needed
