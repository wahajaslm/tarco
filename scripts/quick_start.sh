#!/bin/bash

# WORKFLOW: Quick start script for Trade Compliance API setup and deployment.
# Used by: Development setup, production deployment, quick testing
# Functions:
# 1. Check prerequisites (Docker, Python, etc.)
# 2. Start Docker services
# 3. Run bootstrap script
# 4. Start API server
# 5. Run health checks
# 6. Display usage instructions
#
# Quick start flow: Prerequisites -> Docker up -> Bootstrap -> API start -> Health check -> Ready
# This provides a one-command setup for the complete Trade Compliance API system.

# Quick Start Script for Trade Compliance API

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "All prerequisites are satisfied"
}

# Function to create .env file if it doesn't exist
setup_environment() {
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please review and update .env file with your configuration"
    else
        print_status ".env file already exists"
    fi
}

# Function to start Docker services
start_docker_services() {
    print_status "Starting Docker services..."
    
    # Start services in background
    docker-compose up -d postgres redis ollama qdrant
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if services are running
    if ! docker-compose ps | grep -q "Up"; then
        print_error "Some Docker services failed to start"
        docker-compose logs
        exit 1
    fi
    
    print_success "Docker services started successfully"
}

# Function to run bootstrap script
run_bootstrap() {
    print_status "Running bootstrap script..."
    
    # Check if raw data exists
    if [ -d "data/raw" ] && [ "$(ls -A data/raw)" ]; then
        print_status "Raw data found, processing..."
        python scripts/bootstrap.py
    else
        print_warning "No raw data found, creating sample data..."
        python scripts/bootstrap.py --create-sample
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Bootstrap completed successfully"
    else
        print_error "Bootstrap failed"
        exit 1
    fi
}

# Function to start API server
start_api_server() {
    print_status "Starting API server..."
    
    # Start API service
    docker-compose up -d api
    
    # Wait for API to be ready
    print_status "Waiting for API to be ready..."
    sleep 10
    
    # Check API health
    if curl -f http://localhost:8000/healthz >/dev/null 2>&1; then
        print_success "API server started successfully"
    else
        print_error "API server failed to start"
        docker-compose logs api
        exit 1
    fi
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Check API health
    if curl -f http://localhost:8000/healthz >/dev/null 2>&1; then
        print_success "API health check passed"
    else
        print_error "API health check failed"
        return 1
    fi
    
    # Check database health
    if curl -f http://localhost:8000/readyz >/dev/null 2>&1; then
        print_success "Database health check passed"
    else
        print_error "Database health check failed"
        return 1
    fi
    
    print_success "All health checks passed"
}

# Function to display usage instructions
display_usage() {
    echo ""
    echo "=========================================="
    echo "Trade Compliance API is ready!"
    echo "=========================================="
    echo ""
    echo "API Endpoints:"
    echo "  - Health Check: http://localhost:8000/healthz"
    echo "  - API Documentation: http://localhost:8000/docs"
    echo "  - ReDoc Documentation: http://localhost:8000/redoc"
    echo ""
    echo "Example API calls:"
    echo "  # Deterministic JSON endpoint"
    echo "  curl -X POST http://localhost:8000/api/v1/deterministic-json \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"hs_code\": \"61102000\", \"origin\": \"PK\", \"destination\": \"DE\", \"product_description\": \"cotton hoodies\"}'"
    echo ""
    echo "  # Chat endpoint"
    echo "  curl -X POST http://localhost:8000/api/v1/chat/resolve \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"message\": \"import 1000 cotton hoodies from Pakistan to Germany\"}'"
    echo ""
    echo "Monitoring:"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3000 (admin/admin)"
    echo ""
    echo "Logs:"
    echo "  - API logs: docker-compose logs -f api"
    echo "  - All logs: docker-compose logs -f"
    echo ""
    echo "Stop services:"
    echo "  docker-compose down"
    echo ""
}

# Function to handle cleanup on exit
cleanup() {
    print_status "Cleaning up..."
    # Add any cleanup tasks here
}

# Set up trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    echo "=========================================="
    echo "Trade Compliance API Quick Start"
    echo "=========================================="
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Setup environment
    setup_environment
    
    # Start Docker services
    start_docker_services
    
    # Run bootstrap
    run_bootstrap
    
    # Start API server
    start_api_server
    
    # Run health checks
    run_health_checks
    
    # Display usage instructions
    display_usage
}

# Run main function
main "$@"
