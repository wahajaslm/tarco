# WORKFLOW: ZIP file ingestion for XLSX trade compliance data exports.
# Used by: Data ingestion process, ETL pipeline, database population
# Functions:
# 1. extract_zip_file() - Extract XLSX files from ZIP archive
# 2. parse_xlsx_files() - Parse XLSX files into structured data
# 3. validate_data() - Validate extracted data for consistency
# 4. store_staging_data() - Store data in staging tables
#
# Ingestion flow: ZIP file -> Extract XLSX -> Parse data -> Validate -> Staging tables
# This is the first step in the ETL pipeline for populating the trade compliance database.

"""
ZIP file ingestion for XLSX trade compliance data exports.
"""

import zipfile
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Base

logger = logging.getLogger(__name__)


def extract_zip_file(zip_path: str, extract_dir: str) -> List[str]:
    """
    Extract XLSX files from ZIP archive.
    
    Args:
        zip_path: Path to ZIP file
        extract_dir: Directory to extract files to
        
    Returns:
        List of extracted XLSX file paths
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find all XLSX files
        xlsx_files = list(Path(extract_dir).glob("*.xlsx"))
        logger.info(f"Extracted {len(xlsx_files)} XLSX files from {zip_path}")
        
        return [str(f) for f in xlsx_files]
        
    except Exception as e:
        logger.error(f"Failed to extract ZIP file {zip_path}: {e}")
        raise


def parse_xlsx_files(xlsx_files: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Parse XLSX files into structured data.
    
    Args:
        xlsx_files: List of XLSX file paths
        
    Returns:
        Dictionary mapping sheet names to DataFrames
    """
    dataframes = {}
    
    for file_path in xlsx_files:
        try:
            # Read all sheets from XLSX file
            excel_file = pd.ExcelFile(file_path)
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                key = f"{Path(file_path).stem}_{sheet_name}"
                dataframes[key] = df
                
            logger.info(f"Parsed {len(excel_file.sheet_names)} sheets from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to parse XLSX file {file_path}: {e}")
            continue
    
    return dataframes


def validate_data(dataframes: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Validate extracted data for consistency.
    
    Args:
        dataframes: Dictionary of DataFrames to validate
        
    Returns:
        Dictionary of validated DataFrames
    """
    validated_data = {}
    
    for key, df in dataframes.items():
        try:
            # Basic validation
            if df.empty:
                logger.warning(f"Empty DataFrame for {key}")
                continue
                
            # Remove completely empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            if not df.empty:
                validated_data[key] = df
                logger.info(f"Validated DataFrame {key}: {df.shape}")
            
        except Exception as e:
            logger.error(f"Failed to validate DataFrame {key}: {e}")
            continue
    
    return validated_data


def store_staging_data(dataframes: Dict[str, pd.DataFrame], db: Session) -> None:
    """
    Store data in staging tables.
    
    Args:
        dataframes: Dictionary of validated DataFrames
        db: Database session
    """
    try:
        # This would store data in staging tables
        # For now, just log the data structure
        for key, df in dataframes.items():
            logger.info(f"Staging data for {key}: {df.shape} - Columns: {list(df.columns)}")
        
        logger.info(f"Staged {len(dataframes)} datasets")
        
    except Exception as e:
        logger.error(f"Failed to store staging data: {e}")
        raise


def main(zip_file_path: str, source_name: str) -> None:
    """
    Main ingestion function.
    
    Args:
        zip_file_path: Path to ZIP file containing XLSX exports
        source_name: Name of the data source for provenance tracking
    """
    try:
        logger.info(f"Starting ingestion of {zip_file_path} from source {source_name}")
        
        # Extract ZIP file
        extract_dir = f"data/extracted/{source_name}"
        Path(extract_dir).mkdir(parents=True, exist_ok=True)
        
        xlsx_files = extract_zip_file(zip_file_path, extract_dir)
        
        # Parse XLSX files
        dataframes = parse_xlsx_files(xlsx_files)
        
        # Validate data
        validated_data = validate_data(dataframes)
        
        # Store in staging
        with next(get_db()) as db:
            store_staging_data(validated_data, db)
        
        logger.info(f"Successfully ingested data from {source_name}")
        
    except Exception as e:
        logger.error(f"Ingestion failed for {source_name}: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python ingest_zip.py <zip_file_path> <source_name>")
        sys.exit(1)
    
    zip_file_path = sys.argv[1]
    source_name = sys.argv[2]
    
    main(zip_file_path, source_name)
