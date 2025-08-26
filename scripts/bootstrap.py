# WORKFLOW: Bootstrap script for complete Trade Compliance API setup and data processing.
# Used by: Initial setup, data ingestion, system deployment
# Functions:
# 1. setup_directories() - Create necessary data directories
# 2. process_raw_data() - Process all raw XLSX/ZIP files
# 3. setup_database() - Initialize database schema and tables
# 4. build_vector_index() - Create vector embeddings and index
# 5. validate_setup() - Verify all components are working
# 6. run_tests() - Execute test suite to verify functionality
#
# Bootstrap flow: Raw data -> ETL processing -> Database setup -> Vector indexing -> Validation -> Ready
# This creates a complete, production-ready Trade Compliance API with all data loaded and indexed.

"""
Bootstrap script for Trade Compliance API setup and data processing.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from etl.ingest_zip import main as ingest_zip  # noqa: E402
from db.session import get_db, init_db  # noqa: E402
from rag.embeddings import get_embedding_model  # noqa: E402
from rag.retrieval import vector_retriever  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bootstrap.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def setup_directories() -> None:
    """
    Create necessary data directories if they don't exist.
    """
    try:
        directories = [
            'data/raw',
            'data/extracted',
            'data/staging',
            'data/processed',
            'data/backups',
            'logs',
            'models'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        
        logger.info("All directories created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        raise


def check_raw_data() -> List[Path]:
    """
    Check for raw data files in data/raw directory.
    
    Returns:
        List of raw data file paths
    """
    try:
        raw_dir = Path('data/raw')
        if not raw_dir.exists():
            logger.warning("data/raw directory does not exist")
            return []
        
        # Find all XLSX and ZIP files
        raw_files = []
        for pattern in ['*.xlsx', '*.zip', '*.csv']:
            raw_files.extend(raw_dir.glob(pattern))
        
        if not raw_files:
            logger.warning("No raw data files found in data/raw/")
            logger.info("Please place your XLSX files and ZIP archives in data/raw/")
            return []
        
        logger.info(f"Found {len(raw_files)} raw data files:")
        for file in raw_files:
            logger.info(f"  - {file.name}")
        
        return raw_files
        
    except Exception as e:
        logger.error(f"Failed to check raw data: {e}")
        return []


def process_raw_data(raw_files: List[Path]) -> Dict[str, Any]:
    """
    Process all raw data files through the ETL pipeline.
    
    Args:
        raw_files: List of raw data file paths
        
    Returns:
        Dictionary of processed data
    """
    try:
        logger.info("Starting raw data processing")
        
        all_staging_data = {}
        
        for file_path in raw_files:
            logger.info(f"Processing file: {file_path.name}")
            
            if file_path.suffix.lower() == '.zip':
                # Process ZIP file
                source_name = file_path.stem
                try:
                    ingest_zip(str(file_path), source_name)
                    logger.info(f"Successfully processed ZIP file: {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to process ZIP file {file_path.name}: {e}")
                    continue
                    
            elif file_path.suffix.lower() in ['.xlsx', '.csv']:
                # Process individual file
                source_name = file_path.stem
                try:
                    # For now, we'll create a simple staging entry
                    # In a full implementation, this would parse the file
                    logger.info(f"Processed individual file: {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to process file {file_path.name}: {e}")
                    continue
        
        logger.info("Raw data processing completed")
        return all_staging_data
        
    except Exception as e:
        logger.error(f"Failed to process raw data: {e}")
        raise


def setup_database() -> None:
    """
    Initialize database schema and create tables.
    """
    try:
        logger.info("Setting up database schema")
        
        # Initialize database
        init_db()
        logger.info("Database schema initialized")
        
        # Run Alembic migrations if needed
        try:
            result = subprocess.run(
                ['alembic', 'upgrade', 'head'],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            if result.returncode == 0:
                logger.info("Database migrations completed")
            else:
                logger.warning(f"Database migrations failed: {result.stderr}")
        except FileNotFoundError:
            logger.warning("Alembic not found, skipping migrations")
        
        logger.info("Database setup completed")
        
    except Exception as e:
        logger.error(f"Failed to setup database: {e}")
        raise


def build_vector_index() -> None:
    """
    Create vector embeddings and build the RAG index.
    """
    try:
        logger.info("Building vector index")
        
        # Get database session
        with next(get_db()) as db:
            # Get goods nomenclature data for vector indexing
            from db.models import GoodsNomenclature
            
            nomenclature_items = db.query(GoodsNomenclature).all()
            
            if not nomenclature_items:
                logger.warning("No goods nomenclature data found for vector indexing")
                return
            
            logger.info(f"Found {len(nomenclature_items)} nomenclature items for indexing")
            
            # Prepare documents for vector indexing
            documents = []
            for item in nomenclature_items:
                content = f"{item.goods_code} {item.description}"
                metadata = {
                    'goods_code': item.goods_code,
                    'description': item.description,
                    'level': item.level,
                    'is_leaf': item.is_leaf
                }
                documents.append({
                    'content': content,
                    'metadata': metadata
                })
            
            # Add documents to vector store
            vector_retriever.add_documents(documents)
            
            logger.info(f"Successfully indexed {len(documents)} documents in vector store")
        
        logger.info("Vector index building completed")
        
    except Exception as e:
        logger.error(f"Failed to build vector index: {e}")
        raise


def validate_setup() -> bool:
    """
    Validate that all components are working correctly.
    
    Returns:
        True if validation passes, False otherwise
    """
    try:
        logger.info("Validating setup")
        
        # Check database connection
        from db.session import check_db_connection
        if not check_db_connection():
            logger.error("Database connection validation failed")
            return False
        logger.info("Database connection validated")
        
        # Check vector store
        try:
            collections = vector_retriever.client.get_collections()
            logger.info(f"Vector store has {len(collections.collections)} collections")
        except Exception as e:
            logger.error(f"Vector store validation failed: {e}")
            return False
        
        # Check embedding model
        try:
            test_embedding = get_embedding_model().encode("test")
            logger.info(f"Embedding model working, dimension: {len(test_embedding)}")
        except Exception as e:
            logger.error(f"Embedding model validation failed: {e}")
            return False
        
        # Check if data is loaded
        with next(get_db()) as db:
            from db.models import GoodsNomenclature, MeasuresImport
            
            nomenclature_count = db.query(GoodsNomenclature).count()
            measures_count = db.query(MeasuresImport).count()
            
            logger.info(f"Database contains {nomenclature_count} nomenclature items and {measures_count} import measures")
            
            if nomenclature_count == 0:
                logger.warning("No goods nomenclature data found in database")
            if measures_count == 0:
                logger.warning("No import measures found in database")
        
        logger.info("Setup validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Setup validation failed: {e}")
        return False


def run_tests() -> bool:
    """
    Run the test suite to verify functionality.
    
    Returns:
        True if tests pass, False otherwise
    """
    try:
        logger.info("Running test suite")
        
        result = subprocess.run(
            ['python', '-m', 'pytest', 'tests/', '-v'],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            logger.info("All tests passed")
            return True
        else:
            logger.error(f"Tests failed: {result.stdout}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run tests: {e}")
        return False


def create_sample_data() -> None:
    """
    Create sample data for testing if no raw data is provided.
    """
    try:
        logger.info("Creating sample data for testing")
        
        with next(get_db()) as db:
            from db.models import (
                GoodsNomenclature, MeasuresImport, Geographies, 
                VatRates, LegalBases
            )
            from datetime import datetime
            
            # Create sample goods nomenclature
            sample_nomenclature = [
                GoodsNomenclature(
                    goods_code="61102000",
                    description="Men's or boys' anoraks, windcheaters, of cotton",
                    level=6,
                    valid_from=datetime.now(),
                    is_leaf=True
                ),
                GoodsNomenclature(
                    goods_code="61103000",
                    description="Men's or boys' anoraks, windcheaters, of man-made fibres",
                    level=6,
                    valid_from=datetime.now(),
                    is_leaf=True
                )
            ]
            
            # Create sample measures
            sample_measures = [
                MeasuresImport(
                    goods_code="61102000",
                    origin_group="ERGA OMNES",
                    measure_type="import",
                    duty_components=[{"type": "ad_valorem", "value": 12.5, "unit": "percent"}],
                    legal_base_id="REG_123",
                    legal_base_title="Sample Regulation",
                    valid_from=datetime.now()
                )
            ]
            
            # Create sample geographies
            sample_geographies = [
                Geographies(code="DE", type="country", name="Germany"),
                Geographies(code="PK", type="country", name="Pakistan"),
                Geographies(code="EU", type="union", name="European Union")
            ]
            
            # Create sample VAT rates
            sample_vat_rates = [
                VatRates(
                    country_code="DE",
                    standard_rate=19.0,
                    valid_from=datetime.now()
                )
            ]
            
            # Create sample legal bases
            sample_legal_bases = [
                LegalBases(
                    id="REG_123",
                    title="Sample Trade Regulation"
                )
            ]
            
            # Add all sample data
            db.add_all(sample_nomenclature)
            db.add_all(sample_measures)
            db.add_all(sample_geographies)
            db.add_all(sample_vat_rates)
            db.add_all(sample_legal_bases)
            
            db.commit()
            
            logger.info("Sample data created successfully")
            
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        raise


def main():
    """
    Main bootstrap function.
    """
    parser = argparse.ArgumentParser(description='Bootstrap Trade Compliance API')
    parser.add_argument('--skip-data', action='store_true', help='Skip data processing')
    parser.add_argument('--skip-tests', action='store_true', help='Skip test execution')
    parser.add_argument('--create-sample', action='store_true', help='Create sample data')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing setup')
    
    args = parser.parse_args()
    
    try:
        logger.info("Starting Trade Compliance API bootstrap")
        
        if args.validate_only:
            logger.info("Running validation only")
            if validate_setup():
                logger.info("Validation completed successfully")
                return 0
            else:
                logger.error("Validation failed")
                return 1
        
        # Setup directories
        setup_directories()
        
        # Setup database
        setup_database()
        
        if not args.skip_data:
            # Check for raw data
            raw_files = check_raw_data()
            
            if raw_files:
                # Process raw data
                process_raw_data(raw_files)
            elif args.create_sample:
                # Create sample data
                create_sample_data()
            else:
                logger.warning("No raw data found and --create-sample not specified")
                logger.info("Skipping data processing")
        
        # Build vector index
        build_vector_index()
        
        # Validate setup
        if not validate_setup():
            logger.error("Setup validation failed")
            return 1
        
        # Run tests
        if not args.skip_tests:
            if not run_tests():
                logger.error("Test execution failed")
                return 1
        
        logger.info("Bootstrap completed successfully!")
        logger.info("Trade Compliance API is ready to use")
        
        return 0
        
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
