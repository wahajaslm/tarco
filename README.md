# WORKFLOW: Main documentation for the Trade Compliance API project.
# Used by: Developers, operators, users, deployment teams
# Documentation includes:
# 1. Project overview and mission statement
# 2. Architecture and component descriptions
# 3. Quick start guide and setup instructions
# 4. API endpoint documentation
# 5. Configuration and environment setup
# 6. Testing and deployment procedures
# 7. Troubleshooting and support information
#
# This is the primary reference for understanding, deploying, and operating the system.

# Trade Compliance API

A production-grade Trade Compliance service that returns universal, deterministic JSON for import/export compliance.

## 🎯 Mission

Return a **universal, deterministic JSON** for import/export compliance with strict boundaries:
- **Numeric & Legal Facts**: Database ONLY (ETL from XLSX exports of TARIC, VAT, Import/Export duties)
- **LLMs**: Only for slot extraction, clarification, and human-readable explanations
- **HS Classification**: Learned pipeline (retrieve → rerank → calibrate → abstain if uncertain)
- **Uncertainty**: Return structured `needs_clarification` JSON if HS classification is uncertain

## 🏗️ Architecture

### Core Components
- **FastAPI**: Web framework with structured logging and middleware
- **PostgreSQL + pgvector**: Canonical database with vector extensions
- **Qdrant**: Vector database for RAG operations
- **Ollama**: Local LLM for explanations and slot extraction
- **Redis**: Caching and rate limiting
- **Docker Compose**: Complete service orchestration

### RAG Pipeline
- **Embeddings**: BAAI/bge-m3 for multilingual text encoding
- **Retrieval**: Qdrant vector search with cosine similarity
- **Reranking**: BAAI/bge-reranker-base cross-encoder
- **Calibration**: Logistic regression for confidence scoring
- **Abstention**: Threshold-based uncertainty handling

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- 8GB+ RAM (for ML models)

### One-Command Setup
```bash
# Clone the repository
git clone <repository-url>
cd trade-compliance-api

# Run the quick start script
./scripts/quick_start.sh
```

### Manual Setup
```bash
# 1. Place your raw data files in data/raw/
#    - XLSX files: vat_rates.xlsx, geographies.xlsx, legal_bases.xlsx
#    - ZIP archives: taric_export.zip (containing multiple XLSX files)

# 2. Start Docker services
docker-compose up -d postgres redis ollama qdrant

# 3. Run bootstrap script
python scripts/bootstrap.py --create-sample  # For testing with sample data
# OR
python scripts/bootstrap.py  # For processing your raw data

# 4. Start API server
docker-compose up -d api

# 5. Verify setup
curl http://localhost:8000/healthz
```

## 📁 Data Placement

### Directory Structure
```
data/
├── raw/                    # Place your raw XLSX files and ZIP archives here
│   ├── taric_export.zip    # TARIC export files
│   ├── vat_rates.xlsx      # VAT rate data
│   ├── geographies.xlsx    # Country/region data
│   └── legal_bases.xlsx    # Legal regulation data
├── extracted/              # Temporary extracted files (auto-generated)
├── staging/                # Intermediate data during ETL (auto-generated)
├── processed/              # Final processed data (auto-generated)
└── backups/                # Database backups (auto-generated)
```

### Supported File Formats
- **ZIP archives**: Contain multiple XLSX files (e.g., TARIC exports)
- **XLSX files**: Individual data files (e.g., VAT rates, geographies)
- **CSV files**: Alternative format for simple data

### File Naming Conventions
Use descriptive names for your files:
- `taric_export_YYYYMMDD.zip` - TARIC data exports
- `vat_rates_YYYYMMDD.xlsx` - VAT rate data
- `geographies_YYYYMMDD.xlsx` - Country/region data
- `legal_bases_YYYYMMDD.xlsx` - Legal regulation data

## 🔧 Bootstrapping Process

The bootstrap script (`scripts/bootstrap.py`) performs the complete setup:

1. **Directory Setup**: Creates all necessary data directories
2. **Database Initialization**: Sets up PostgreSQL schema and tables
3. **Data Processing**: 
   - Extracts ZIP files to `data/extracted/`
   - Parses XLSX files into structured data
   - Validates data consistency and quality
   - Transforms data to canonical schema
   - Loads data into PostgreSQL database
4. **Vector Indexing**: Creates embeddings and builds Qdrant vector index
5. **Validation**: Verifies all components are working correctly
6. **Testing**: Runs test suite to ensure functionality

### Bootstrap Options
```bash
# Process raw data files
python scripts/bootstrap.py

# Create sample data for testing
python scripts/bootstrap.py --create-sample

# Skip data processing
python scripts/bootstrap.py --skip-data

# Skip test execution
python scripts/bootstrap.py --skip-tests

# Validate existing setup only
python scripts/bootstrap.py --validate-only
```

## 📊 Data Processing Workflow

1. **Extract**: ZIP files are extracted to `data/extracted/`
2. **Parse**: XLSX files are parsed into structured data
3. **Validate**: Data is validated for consistency and quality
4. **Transform**: Data is transformed to canonical schema
5. **Load**: Data is loaded into PostgreSQL database
6. **Index**: Vector embeddings are created and stored in Qdrant

## 🛠️ API Endpoints

### Deterministic Endpoints
```bash
# Get deterministic compliance data
curl -X POST http://localhost:8000/api/v1/deterministic-json \
  -H 'Content-Type: application/json' \
  -d '{
    "hs_code": "61102000",
    "origin": "PK",
    "destination": "DE",
    "product_description": "cotton hoodies"
  }'

# Get deterministic data with LLM explanations
curl -X POST http://localhost:8000/api/v1/deterministic-json+explain \
  -H 'Content-Type: application/json' \
  -d '{
    "hs_code": "61102000",
    "origin": "PK",
    "destination": "DE",
    "product_description": "cotton hoodies"
  }'
```

### Chat Endpoints
```bash
# Natural language HS classification
curl -X POST http://localhost:8000/api/v1/chat/resolve \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "import 1000 cotton hoodies from Pakistan to Germany"
  }'

# Answer clarification questions
curl -X POST http://localhost:8000/api/v1/chat/answer \
  -H 'Content-Type: application/json' \
  -d '{
    "question_id": "cq_1",
    "selected_option": "a"
  }'
```

### Health Endpoints
```bash
# Basic health check
curl http://localhost:8000/healthz

# Readiness check with dependencies
curl http://localhost:8000/readyz

# Liveness check
curl http://localhost:8000/livez
```

## 🔍 Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

### Run Test Suite
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_workflow.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

The test suite stubs out calls to the Ollama LLM so no external model is
invoked. See `tests/test_query_parameters.py` for the mocking helper used to
return deterministic JSON payloads.

### Test the Cotton Hoodie Workflow
```bash
# This test validates the complete workflow from the requirements
python -m pytest tests/test_workflow.py::test_cotton_hoodie_workflow -v
```

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://tarco:tarco@postgres:5432/tarco

# Vector Search
QDRANT_URL=http://qdrant:6333
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-base

# LLM
OLLAMA_URL=http://ollama:11434
LLM_MODEL=llama2:7b

# Classification
CONFIDENCE_THRESHOLD=0.62
MARGIN_THRESHOLD=0.07

# Security
SECRET_KEY=your-secret-key-here
```

## 🚀 Deployment

### Production Deployment
```bash
# Build and push Docker images
docker-compose build
docker-compose push

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

### Development
```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## 📈 Quality Bars

- **Latency**: p95 ≤ 500ms for confident classifications
- **Accuracy**: Zero schema violations in CI
- **Reliability**: Zero invented numbers in LLM explanations
- **Coverage**: All numeric facts from database only

## 🔍 Troubleshooting

### Common Issues

1. **No raw data found**
   - Place XLSX files in `data/raw/` directory
   - Use `--create-sample` flag for testing

2. **Database connection failed**
   - Check if PostgreSQL container is running: `docker-compose ps`
   - Check logs: `docker-compose logs postgres`

3. **Vector search not working**
   - Verify Qdrant is running: `docker-compose ps qdrant`
   - Check vector index: `curl http://localhost:6333/collections`

4. **LLM service unavailable**
   - Check Ollama container: `docker-compose logs ollama`
   - Verify model is downloaded: `curl http://localhost:11434/api/tags`

### Logs and Debugging
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f qdrant

# Check bootstrap logs
tail -f logs/bootstrap.log
```

## 📚 Documentation

- **API Documentation**: http://localhost:8000/docs
- **Operational Runbook**: [RUNBOOK.md](RUNBOOK.md)
- **Data Directory Guide**: [data/README.md](data/README.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

[License information]

## 🆘 Support

- Check the documentation for common questions
- Review the test cases for usage examples
- Open an issue for bugs or feature requests
