# WORKFLOW: Lightweight bootstrap script for Trade Compliance API setup.
# Used by: Initial setup, development, testing
# Functions:
# 1. setup_directories() - Create necessary directories
# 2. setup_database() - Initialize database schema
# 3. create_sample_data() - Add sample data for testing
# 4. validate_setup() - Verify basic functionality
#
# Bootstrap flow: Directories -> Database -> Sample Data -> Validation -> Ready
# This provides a working system without heavy ML dependencies initially.

"""
Lightweight bootstrap script for Trade Compliance API setup.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def setup_directories() -> None:
    """Create necessary directories."""
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


def setup_database() -> None:
    """Initialize database schema."""
    try:
        logger.info("Setting up database schema")
        
        # Import database components
        from db.session import engine
        from db.models import Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")
        
        # Run Alembic migrations if available
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
    """Create sample data for testing."""
    try:
        logger.info("Creating sample data for testing")
        
        from db.session import get_db
        from db.models import (
            GoodsNomenclature, MeasuresImport, Geographies, 
            VatRates, LegalBases
        )
        from datetime import datetime
        
        db = next(get_db())
        
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
            ),
            GoodsNomenclature(
                goods_code="62034290",
                description="Men's or boys' trousers, of cotton, other than shorts",
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
            ),
            MeasuresImport(
                goods_code="61102000",
                origin_group="PK",
                measure_type="import",
                duty_components=[{"type": "ad_valorem", "value": 8.5, "unit": "percent"}],
                legal_base_id="REG_456",
                legal_base_title="GSP Regulation",
                valid_from=datetime.now()
            )
        ]
        
        # Create sample geographies
        sample_geographies = [
            Geographies(code="DE", type="country", name="Germany"),
            Geographies(code="PK", type="country", name="Pakistan"),
            Geographies(code="EU", type="union", name="European Union"),
            Geographies(code="ERGA OMNES", type="group", name="All Countries")
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
            ),
            LegalBases(
                id="REG_456",
                title="GSP Regulation"
            )
        ]
        
        # Add all sample data
        db.add_all(sample_nomenclature)
        db.add_all(sample_measures)
        db.add_all(sample_geographies)
        db.add_all(sample_vat_rates)
        db.add_all(sample_legal_bases)
        
        db.commit()
        db.close()
        
        logger.info("Sample data created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        raise


def validate_setup() -> bool:
    """Validate that the setup is working."""
    try:
        logger.info("Validating setup")
        
        from db.session import get_db
        from db.models import GoodsNomenclature, MeasuresImport
        
        db = next(get_db())
        
        # Check if data is loaded
        nomenclature_count = db.query(GoodsNomenclature).count()
        measures_count = db.query(MeasuresImport).count()
        
        logger.info(f"Database contains {nomenclature_count} nomenclature items and {measures_count} import measures")
        
        if nomenclature_count == 0:
            logger.warning("No goods nomenclature data found in database")
        if measures_count == 0:
            logger.warning("No import measures found in database")
        
        db.close()
        
        logger.info("Setup validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Setup validation failed: {e}")
        return False


def test_api_endpoint() -> bool:
    """Test a basic API endpoint."""
    try:
        logger.info("Testing API endpoint")
        
        import requests
        import time
        
        # Wait for API to be ready
        time.sleep(5)
        
        response = requests.get("http://localhost:8000/healthz", timeout=10)
        if response.status_code == 200:
            logger.info("API health check passed")
            return True
        else:
            logger.warning(f"API health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.warning(f"API test failed: {e}")
        return False


def main():
    """Main bootstrap function."""
    parser = argparse.ArgumentParser(description='Lightweight Bootstrap Trade Compliance API')
    parser.add_argument('--create-sample', action='store_true', help='Create sample data')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing setup')
    parser.add_argument('--test-api', action='store_true', help='Test API endpoint')
    
    args = parser.parse_args()
    
    try:
        logger.info("Starting Trade Compliance API lightweight bootstrap")
        
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
        
        # Create sample data
        if args.create_sample or True:  # Always create sample data for now
            create_sample_data()
        
        # Validate setup
        if not validate_setup():
            logger.error("Setup validation failed")
            return 1
        
        # Test API if requested
        if args.test_api:
            if not test_api_endpoint():
                logger.warning("API test failed, but setup is complete")
        
        logger.info("Lightweight bootstrap completed successfully!")
        logger.info("Database is ready with sample data.")
        logger.info("You can now start the API with: docker-compose up api")
        
        return 0
        
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
