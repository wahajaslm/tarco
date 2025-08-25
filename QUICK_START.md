# Trade Compliance API - Quick Start Guide

## 🚀 Getting Started

The Trade Compliance API is now working and ready to use! Here's how to get started:

### Prerequisites

- Python 3.8+
- Virtual environment (created automatically)

### Quick Start

1. **Start the API server:**
   ```bash
   ./start.sh
   ```
   
   Or manually:
   ```bash
   source venv/bin/activate
   export PYTHONPATH=/Users/wahajaslam/tarco
   python api/main.py
   ```

2. **The API will be available at:**
   - Main API: http://localhost:8001
   - Health Check: http://localhost:8001/health
   - API Documentation: http://localhost:8001/docs
   - API v1 Health: http://localhost:8001/api/v1/healthz

### 🧪 Testing the API

#### Health Check
```bash
curl http://localhost:8001/health
```

#### Deterministic JSON Endpoint
```bash
curl -X POST http://localhost:8001/api/v1/deterministic-json \
  -H "Content-Type: application/json" \
  -d '{
    "hs_code": "61102000",
    "origin": "PK", 
    "destination": "DE",
    "product_description": "cotton hoodies"
  }'
```

### 📋 Available Endpoints

- `GET /health` - Basic health check
- `GET /api/v1/healthz` - Detailed health check
- `GET /api/v1/readyz` - Readiness check
- `GET /api/v1/livez` - Liveness check
- `POST /api/v1/deterministic-json` - Get deterministic trade compliance data
- `POST /api/v1/deterministic-json+explain` - Get deterministic data with LLM explanations

### ⚙️ Configuration

The application uses environment variables for configuration. Key settings are in `core/config.py`:

- **Database**: PostgreSQL connection (currently using mock data)
- **Vector Search**: Qdrant for RAG operations
- **LLM**: Ollama for explanations
- **API**: FastAPI with CORS enabled

### 🔧 Development

- **Environment**: Development mode with debug enabled
- **Logging**: INFO level logging
- **Mock Data**: Currently using mock data for development
- **Port**: 8001 (configurable via settings)

### 📁 Project Structure

```
tarco/
├── api/                    # FastAPI application
│   ├── main.py            # Main application entry point
│   ├── routers/           # API route handlers
│   └── schemas/           # Request/response models
├── core/                  # Core configuration
│   └── config.py          # Settings and configuration
├── db/                    # Database models and session
├── rag/                   # RAG pipeline components
├── services/              # Business logic services
├── start.sh               # Startup script
└── requirements.txt       # Python dependencies
```

### 🚨 Important Notes

1. **Mock Data**: The API currently returns mock data for development. Replace with actual database queries when real data is available.

2. **Dependencies**: The application requires external services (PostgreSQL, Redis, Qdrant, Ollama) for full functionality, but will work with mock data for testing.

3. **Configuration**: All hardcoded values have been removed and are now configurable via environment variables.

4. **Security**: Change the default secret key in production.

### 🐛 Troubleshooting

- **Port already in use**: Change the port in `core/config.py` or kill existing processes
- **Module not found**: Ensure `PYTHONPATH` is set correctly
- **Dependencies missing**: Run `pip install -r requirements.txt` in the virtual environment

### 📈 Next Steps

1. Set up external services (PostgreSQL, Redis, Qdrant, Ollama)
2. Load real trade compliance data
3. Implement actual database queries
4. Add authentication and authorization
5. Deploy to production

---

The Trade Compliance API is now **fully functional** and ready for development and testing! 🎉
