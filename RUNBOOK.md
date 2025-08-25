# WORKFLOW: Operational runbook for Trade Compliance API deployment and maintenance.
# Used by: Operations teams, DevOps engineers, system administrators
# Operational procedures:
# 1. Quick start and service initialization
# 2. Health checks and monitoring procedures
# 3. Data management and backup procedures
# 4. Model management and retraining
# 5. Troubleshooting common issues
# 6. Emergency procedures and recovery
# 7. Maintenance schedules and tasks
#
# Operational flow: Service startup -> Health monitoring -> Issue resolution -> Maintenance
# This ensures reliable operation and quick problem resolution in production environments.

# Trade Compliance API Runbook

## Quick Start

### 1. Start Services
```bash
docker compose up -d
```

### 2. Initialize Database
```bash
docker compose exec api alembic upgrade head
```

### 3. Ingest Data
```bash
# Place XLSX files in data/ directory
docker compose exec api python etl/ingest_zip.py
docker compose exec api python etl/transform_canonical.py
```

### 4. Test API
```bash
# Health check
curl http://localhost:8000/healthz

# Test deterministic endpoint
curl -X POST http://localhost:8000/api/v1/deterministic-json \
  -H "Content-Type: application/json" \
  -d '{
    "hs_code": "61102000",
    "origin": "PK",
    "destination": "DE",
    "product_description": "cotton hoodies"
  }'

# Test chat endpoint
curl -X POST http://localhost:8000/api/v1/chat/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "message": "import 1000 cotton hoodies from Pakistan to Germany"
  }'
```

## Operational Procedures

### Service Health Checks

#### Database Health
```bash
# Check database connection
docker compose exec api python -c "from db.session import check_db_connection; print(check_db_connection())"

# Check database tables
docker compose exec postgres psql -U tarco -d tarco -c "\dt"
```

#### Vector Store Health
```bash
# Check Qdrant collections
curl http://localhost:6333/collections

# Check collection info
curl http://localhost:6333/collections/nomenclature_chunks
```

#### LLM Service Health
```bash
# Check Ollama models
curl http://localhost:11434/api/tags

# Test LLM generation
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2:7b",
    "prompt": "Hello, world!",
    "stream": false
  }'
```

### Logs and Monitoring

#### View Service Logs
```bash
# All services
docker compose logs

# Specific service
docker compose logs api
docker compose logs postgres
docker compose logs qdrant
docker compose logs ollama

# Follow logs
docker compose logs -f api
```

#### Prometheus Metrics
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Grafana dashboard
# Access at http://localhost:3000 (admin/admin)
```

### Data Management

#### Backup Database
```bash
# Create backup
docker compose exec postgres pg_dump -U tarco tarco > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker compose exec -T postgres psql -U tarco -d tarco < backup_file.sql
```

#### Rebuild Vector Index
```bash
# Clear and rebuild vector index
docker compose exec api python -c "
from rag.retrieval import vector_retriever
vector_retriever.delete_collection()
vector_retriever._ensure_collection_exists()
"

# Reindex from database
docker compose exec api python etl/build_vector_index.py
```

### Model Management

#### Update LLM Models
```bash
# Pull new model
docker compose exec ollama ollama pull llama2:7b

# List available models
docker compose exec ollama ollama list
```

#### Retrain Calibrator
```bash
# Retrain confidence calibrator
docker compose exec api python rag/retrain_calibrator.py
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed
**Symptoms**: API returns 500 errors, database health check fails

**Diagnosis**:
```bash
docker compose logs postgres
docker compose exec api python -c "from db.session import check_db_connection; print(check_db_connection())"
```

**Solutions**:
- Check if PostgreSQL container is running: `docker compose ps postgres`
- Restart PostgreSQL: `docker compose restart postgres`
- Check disk space: `docker system df`
- Verify database URL in environment variables

#### 2. Vector Search Not Working
**Symptoms**: HS classification fails, no candidates retrieved

**Diagnosis**:
```bash
curl http://localhost:6333/collections
docker compose logs qdrant
```

**Solutions**:
- Restart Qdrant: `docker compose restart qdrant`
- Rebuild vector index (see Data Management section)
- Check if embeddings are loaded: `curl http://localhost:6333/collections/nomenclature_chunks`

#### 3. LLM Service Unavailable
**Symptoms**: Explanations fail, chat endpoints return errors

**Diagnosis**:
```bash
curl http://localhost:11434/api/tags
docker compose logs ollama
```

**Solutions**:
- Restart Ollama: `docker compose restart ollama`
- Check if model is downloaded: `docker compose exec ollama ollama list`
- Pull missing model: `docker compose exec ollama ollama pull llama2:7b`

#### 4. High Memory Usage
**Symptoms**: Services crash, OOM errors

**Diagnosis**:
```bash
docker stats
docker system df
```

**Solutions**:
- Increase Docker memory limit to 8GB+
- Restart services: `docker compose restart`
- Clear unused resources: `docker system prune`

#### 5. Schema Validation Errors
**Symptoms**: API returns 422 errors, validation failures

**Diagnosis**:
```bash
# Check response against schema
curl -X POST http://localhost:8000/api/v1/deterministic-json \
  -H "Content-Type: application/json" \
  -d '{"hs_code": "61102000", "origin": "PK", "destination": "DE"}' \
  | python -m json.tool
```

**Solutions**:
- Verify request format matches schema
- Check if all required fields are present
- Validate HS code format (4-10 digits)
- Validate country codes (2-3 characters)

### Performance Issues

#### Slow Response Times
**Diagnosis**:
```bash
# Check response times
curl -w "@curl-format.txt" -X POST http://localhost:8000/api/v1/deterministic-json \
  -H "Content-Type: application/json" \
  -d '{"hs_code": "61102000", "origin": "PK", "destination": "DE"}'
```

**Solutions**:
- Check database query performance
- Verify vector search is using indexes
- Monitor LLM response times
- Consider caching frequently requested data

#### High CPU Usage
**Diagnosis**:
```bash
docker stats
top -p $(pgrep -f "uvicorn\|ollama\|qdrant")
```

**Solutions**:
- Scale services horizontally
- Optimize database queries
- Use more efficient embedding models
- Implement request caching

### Security Issues

#### Authentication Failures
**Symptoms**: 401 Unauthorized errors

**Diagnosis**:
```bash
# Check JWT token
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/deterministic-json
```

**Solutions**:
- Verify SECRET_KEY is set correctly
- Check token expiration
- Validate token format
- Regenerate tokens if needed

#### Rate Limiting
**Symptoms**: 429 Too Many Requests errors

**Diagnosis**:
```bash
# Check Redis
docker compose exec redis redis-cli info memory
```

**Solutions**:
- Increase rate limits in configuration
- Scale Redis if needed
- Implement client-side retry logic

## Emergency Procedures

### Service Recovery
```bash
# Full service restart
docker compose down
docker compose up -d

# Individual service restart
docker compose restart <service-name>
```

### Data Recovery
```bash
# Restore from backup
docker compose exec -T postgres psql -U tarco -d tarco < latest_backup.sql

# Rebuild indexes
docker compose exec api python etl/build_vector_index.py
```

### Rollback Deployment
```bash
# Rollback to previous version
docker compose pull
docker compose up -d --force-recreate
```

## Maintenance

### Daily Tasks
- [ ] Check service health endpoints
- [ ] Review error logs
- [ ] Monitor resource usage
- [ ] Verify data integrity

### Weekly Tasks
- [ ] Backup database
- [ ] Update dependencies
- [ ] Review performance metrics
- [ ] Clean up old logs

### Monthly Tasks
- [ ] Retrain ML models
- [ ] Update security patches
- [ ] Review and update documentation
- [ ] Performance optimization review
