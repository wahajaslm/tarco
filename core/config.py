# WORKFLOW: Core configuration management for the Trade Compliance API.
# Used by: All modules throughout the application
# Configuration includes:
# - Database connection settings
# - Vector search parameters (Qdrant, embedding models)
# - LLM settings (Ollama, model names)
# - Security settings (JWT, API keys)
# - Classification thresholds (confidence, margin)
# - API settings (CORS, rate limiting)
# - Monitoring and logging configuration
#
# Loaded at startup and used by all services for consistent configuration.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://tarco:tarco@localhost:5432/tarco"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # LLM
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "llama2:7b"
    
    # Vector Search (Lightweight)
    qdrant_url: str = ":memory:"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    vector_dimension: int = 384
    model_cache_dir: str = "./.cache/huggingface"
    top_k_retrieval: int = 32
    top_k_rerank: int = 5
    
    # Classification
    confidence_threshold: float = 0.62
    margin_threshold: float = 0.07
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Trade Compliance API"
    version: str = "1.0.0"
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    allowed_origins: list[str] = ["*"]
    allowed_methods: list[str] = ["*"]
    allowed_headers: list[str] = ["*"]
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 8002
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        protected_namespaces = ('settings_',)


settings = Settings()
