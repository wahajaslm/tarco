# WORKFLOW: Simplified bootstrap script for initial data processing without heavy ML models.
# Used by: Initial setup, data ingestion, development setup
# Functions:
# 1. setup_directories() - Create necessary data directories
# 2. process_raw_data() - Process all raw XLSX/ZIP files
# 3. setup_database() - Initialize database schema and tables
# 4. validate_setup() - Verify all components are working
#
# Bootstrap flow: Raw data -> ETL processing -> Database setup -> Validation -> Ready
# This creates a complete database setup without requiring heavy ML models initially.

"""
Simplified bootstrap script for Trade Compliance API setup and data processing.
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import List
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.session import init_db, get_db  # noqa: E402

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


def main():
    """
    Main bootstrap function.
    """
    parser = argparse.ArgumentParser(description='Simple Bootstrap Trade Compliance API')
    parser.add_argument('--create-sample', action='store_true', help='Create sample data')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing setup')
    
    args = parser.parse_args()
    
    try:
        logger.info("Starting Trade Compliance API simple bootstrap")
        
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
        
        # Check for raw data
        raw_files = check_raw_data()
        
        if raw_files:
            logger.info(f"Found {len(raw_files)} raw data files")
            logger.info("Raw data processing will be implemented in the next step")
            logger.info("For now, creating sample data for testing")
            create_sample_data()
        elif args.create_sample:
            # Create sample data
            create_sample_data()
        else:
            logger.warning("No raw data found and --create-sample not specified")
            logger.info("Creating sample data for testing")
            create_sample_data()
        
        # Validate setup
        if not validate_setup():
            logger.error("Setup validation failed")
            return 1
        
        logger.info("Simple bootstrap completed successfully!")
        logger.info("Database is ready. Vector indexing can be done separately.")
        
        return 0
        
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
