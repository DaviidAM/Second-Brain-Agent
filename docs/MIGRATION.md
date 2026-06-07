# Migration Guide

## Version Upgrade Procedure

1. **Backup data**
   ```bash
   tar -czf backup-$(date +%Y%m%d).tar.gz knowledge/wiki .metadata
   ```

2. **Check release notes**
   - Review breaking changes
   - Note deprecated features

3. **Update configuration**
   - Review new environment variables
   - Update config files if needed

4. **Deploy new version**
   ```bash
   # Docker
   docker pull mcp-server:latest
   
   # Kubernetes
   kubectl set image deployment/mcp-server mcp-server=mcp-server:latest
   ```

5. **Verify migration**
   - Run health checks
   - Test query endpoint
   - Verify index integrity

## Data Migration

### Wiki Structure Changes

If wiki structure changes between versions:

1. Run migration script:
   ```bash
   python -m src.mcp.migrate --from-version X --to-version Y
   ```

2. Verify all documents are accessible

### Index Rebuild

If index format changes:

```bash
python -m src.mcp.indexing --rebuild
```

## Configuration Migration

### Environment Variables

Review `docs/ENVIRONMENT_VARS.md` for new/changed variables.

Example migration script:
```bash
# Export old config
export | grep MCP > old-config.sh

# Review and update
vim old-config.sh

# Apply new config
source new-config.sh
```

## Rollback Procedure

See `docs/ROLLBACK.md` for detailed rollback steps.
