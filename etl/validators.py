# WORKFLOW: Data validation for ETL pipeline consistency and integrity checks.
# Used by: ETL pipeline, data quality assurance, error detection
# Functions:
# 1. validate_goods_nomenclature() - Validate HS codes and descriptions
# 2. validate_measures() - Validate import/export measures
# 3. validate_geographies() - Validate country codes and groupings
# 4. validate_vat_rates() - Validate VAT rate data
# 5. validate_legal_bases() - Validate legal regulation data
# 6. validate_data_consistency() - Cross-reference validation
# 7. generate_validation_report() - Create validation summary
#
# Validation flow: Staging data -> Schema validation -> Business rules -> Consistency checks -> Report
# This ensures data quality and identifies issues before loading into canonical tables.

"""
Data validation for ETL pipeline consistency and integrity checks.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def validate_hs_code(hs_code: str) -> bool:
    """
    Validate HS code format.
    
    Args:
        hs_code: HS code to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not hs_code or not isinstance(hs_code, str):
            return False
        
        # HS codes should be 4-10 digits
        if not re.match(r'^\d{4,10}$', hs_code.strip()):
            return False
        
        return True
        
    except Exception:
        return False


def validate_country_code(country_code: str) -> bool:
    """
    Validate country code format.
    
    Args:
        country_code: Country code to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not country_code or not isinstance(country_code, str):
            return False
        
        # Country codes should be 2-3 characters
        if not re.match(r'^[A-Z]{2,3}$', country_code.strip()):
            return False
        
        return True
        
    except Exception:
        return False


def validate_goods_nomenclature(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate goods nomenclature data.
    
    Args:
        df: DataFrame containing goods nomenclature data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        required_columns = ['goods_code', 'description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
        
        if 'goods_code' in df.columns:
            # Validate HS codes
            invalid_hs_codes = []
            for idx, row in df.iterrows():
                hs_code = str(row.get('goods_code', ''))
                if not validate_hs_code(hs_code):
                    invalid_hs_codes.append(f"Row {idx}: {hs_code}")
            
            if invalid_hs_codes:
                errors.append(f"Invalid HS codes: {invalid_hs_codes[:10]}...")  # Limit to first 10
        
        if 'description' in df.columns:
            # Check for empty descriptions
            empty_descriptions = df[df['description'].isna() | (df['description'] == '')]
            if not empty_descriptions.empty:
                errors.append(f"Empty descriptions found in {len(empty_descriptions)} rows")
        
        if 'level' in df.columns:
            # Validate levels
            invalid_levels = df[~df['level'].isin([0, 1, 2, 3, 4, 5, 6])]
            if not invalid_levels.empty:
                errors.append(f"Invalid levels found in {len(invalid_levels)} rows")
        
        logger.info(f"Goods nomenclature validation: {len(errors)} errors found")
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return False, errors


def validate_measures(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate measures data.
    
    Args:
        df: DataFrame containing measures data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        required_columns = ['goods_code', 'measure_type', 'duty_components']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
        
        if 'goods_code' in df.columns:
            # Validate HS codes
            invalid_hs_codes = []
            for idx, row in df.iterrows():
                hs_code = str(row.get('goods_code', ''))
                if not validate_hs_code(hs_code):
                    invalid_hs_codes.append(f"Row {idx}: {hs_code}")
            
            if invalid_hs_codes:
                errors.append(f"Invalid HS codes: {invalid_hs_codes[:10]}...")
        
        if 'measure_type' in df.columns:
            # Validate measure types
            valid_types = ['import', 'export', 'prohibited', 'quota', 'suspension']
            invalid_types = df[~df['measure_type'].isin(valid_types)]
            if not invalid_types.empty:
                errors.append(f"Invalid measure types found in {len(invalid_types)} rows")
        
        if 'duty_components' in df.columns:
            # Check for empty duty components
            empty_duties = df[df['duty_components'].isna() | (df['duty_components'] == '')]
            if not empty_duties.empty:
                errors.append(f"Empty duty components found in {len(empty_duties)} rows")
        
        logger.info(f"Measures validation: {len(errors)} errors found")
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return False, errors


def validate_geographies(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate geography data.
    
    Args:
        df: DataFrame containing geography data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        required_columns = ['code', 'type', 'name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
        
        if 'code' in df.columns:
            # Validate country codes
            invalid_codes = []
            for idx, row in df.iterrows():
                code = str(row.get('code', ''))
                if not validate_country_code(code):
                    invalid_codes.append(f"Row {idx}: {code}")
            
            if invalid_codes:
                errors.append(f"Invalid country codes: {invalid_codes[:10]}...")
        
        if 'type' in df.columns:
            # Validate geography types
            valid_types = ['country', 'group', 'region', 'union']
            invalid_types = df[~df['type'].isin(valid_types)]
            if not invalid_types.empty:
                errors.append(f"Invalid geography types found in {len(invalid_types)} rows")
        
        if 'name' in df.columns:
            # Check for empty names
            empty_names = df[df['name'].isna() | (df['name'] == '')]
            if not empty_names.empty:
                errors.append(f"Empty names found in {len(empty_names)} rows")
        
        logger.info(f"Geographies validation: {len(errors)} errors found")
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return False, errors


def validate_vat_rates(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate VAT rate data.
    
    Args:
        df: DataFrame containing VAT rate data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        required_columns = ['country_code', 'standard_rate']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
        
        if 'country_code' in df.columns:
            # Validate country codes
            invalid_codes = []
            for idx, row in df.iterrows():
                code = str(row.get('country_code', ''))
                if not validate_country_code(code):
                    invalid_codes.append(f"Row {idx}: {code}")
            
            if invalid_codes:
                errors.append(f"Invalid country codes: {invalid_codes[:10]}...")
        
        if 'standard_rate' in df.columns:
            # Validate VAT rates (should be between 0 and 100)
            invalid_rates = df[
                (df['standard_rate'] < 0) | 
                (df['standard_rate'] > 100) | 
                df['standard_rate'].isna()
            ]
            if not invalid_rates.empty:
                errors.append(f"Invalid standard rates found in {len(invalid_rates)} rows")
        
        if 'reduced_rate_1' in df.columns:
            # Validate reduced rates
            invalid_reduced = df[
                (df['reduced_rate_1'] < 0) | 
                (df['reduced_rate_1'] > 100) | 
                (df['reduced_rate_1'] > df['standard_rate'])
            ]
            if not invalid_reduced.empty:
                errors.append(f"Invalid reduced rates found in {len(invalid_reduced)} rows")
        
        logger.info(f"VAT rates validation: {len(errors)} errors found")
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return False, errors


def validate_legal_bases(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate legal bases data.
    
    Args:
        df: DataFrame containing legal bases data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        required_columns = ['id', 'title']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
        
        if 'id' in df.columns:
            # Check for duplicate IDs
            duplicates = df[df['id'].duplicated()]
            if not duplicates.empty:
                errors.append(f"Duplicate IDs found in {len(duplicates)} rows")
        
        if 'title' in df.columns:
            # Check for empty titles
            empty_titles = df[df['title'].isna() | (df['title'] == '')]
            if not empty_titles.empty:
                errors.append(f"Empty titles found in {len(empty_titles)} rows")
        
        logger.info(f"Legal bases validation: {len(errors)} errors found")
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return False, errors


def validate_data_consistency(staging_data: Dict[str, pd.DataFrame]) -> Tuple[bool, List[str]]:
    """
    Validate data consistency across different datasets.
    
    Args:
        staging_data: Dictionary of staging DataFrames
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        # Extract HS codes from different datasets
        hs_codes = set()
        
        # From goods nomenclature
        if 'goods_nomenclature' in staging_data:
            df = staging_data['goods_nomenclature']
            if 'goods_code' in df.columns:
                hs_codes.update(df['goods_code'].dropna().astype(str).tolist())
        
        # From measures
        for key, df in staging_data.items():
            if 'measure' in key.lower() and 'goods_code' in df.columns:
                measure_hs_codes = set(df['goods_code'].dropna().astype(str).tolist())
                # Check if all measure HS codes exist in goods nomenclature
                if 'goods_nomenclature' in staging_data:
                    nomenclature_hs_codes = set(staging_data['goods_nomenclature']['goods_code'].dropna().astype(str).tolist())
                    missing_codes = measure_hs_codes - nomenclature_hs_codes
                    if missing_codes:
                        errors.append(f"HS codes in measures not found in nomenclature: {list(missing_codes)[:10]}...")
        
        # Extract country codes
        country_codes = set()
        
        # From geographies
        if 'geographies' in staging_data:
            df = staging_data['geographies']
            if 'code' in df.columns:
                country_codes.update(df['code'].dropna().astype(str).tolist())
        
        # From VAT rates
        if 'vat_rates' in staging_data:
            df = staging_data['vat_rates']
            if 'country_code' in df.columns:
                vat_country_codes = set(df['country_code'].dropna().astype(str).tolist())
                # Check if all VAT country codes exist in geographies
                if 'geographies' in staging_data:
                    geo_country_codes = set(staging_data['geographies']['code'].dropna().astype(str).tolist())
                    missing_codes = vat_country_codes - geo_country_codes
                    if missing_codes:
                        errors.append(f"Country codes in VAT rates not found in geographies: {list(missing_codes)[:10]}...")
        
        logger.info(f"Data consistency validation: {len(errors)} errors found")
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"Consistency validation error: {str(e)}")
        return False, errors


def generate_validation_report(validation_results: Dict[str, Tuple[bool, List[str]]]) -> Dict[str, Any]:
    """
    Generate validation report.
    
    Args:
        validation_results: Dictionary of validation results
        
    Returns:
        Validation report dictionary
    """
    try:
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_valid': True,
            'datasets': {},
            'summary': {
                'total_datasets': len(validation_results),
                'valid_datasets': 0,
                'invalid_datasets': 0,
                'total_errors': 0
            }
        }
        
        for dataset_name, (is_valid, errors) in validation_results.items():
            report['datasets'][dataset_name] = {
                'valid': is_valid,
                'error_count': len(errors),
                'errors': errors
            }
            
            if is_valid:
                report['summary']['valid_datasets'] += 1
            else:
                report['summary']['invalid_datasets'] += 1
                report['overall_valid'] = False
            
            report['summary']['total_errors'] += len(errors)
        
        logger.info(f"Validation report generated: {report['summary']}")
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate validation report: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_valid': False,
            'error': str(e)
        }


def validate_staging_data(staging_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Validate all staging data.
    
    Args:
        staging_data: Dictionary of staging DataFrames
        
    Returns:
        Validation report
    """
    try:
        logger.info("Starting validation of staging data")
        
        validation_results = {}
        
        # Validate individual datasets
        for key, df in staging_data.items():
            if 'goods' in key.lower() or 'nomenclature' in key.lower():
                validation_results[key] = validate_goods_nomenclature(df)
            elif 'measure' in key.lower():
                validation_results[key] = validate_measures(df)
            elif 'geo' in key.lower() or 'country' in key.lower():
                validation_results[key] = validate_geographies(df)
            elif 'vat' in key.lower():
                validation_results[key] = validate_vat_rates(df)
            elif 'legal' in key.lower() or 'regulation' in key.lower():
                validation_results[key] = validate_legal_bases(df)
            else:
                # Generic validation for unknown datasets
                validation_results[key] = (True, [])
        
        # Validate data consistency
        consistency_valid, consistency_errors = validate_data_consistency(staging_data)
        validation_results['consistency'] = (consistency_valid, consistency_errors)
        
        # Generate report
        report = generate_validation_report(validation_results)
        
        logger.info(f"Validation completed: {report['summary']}")
        return report
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_valid': False,
            'error': str(e)
        }


if __name__ == "__main__":
    # Test validation functions
    test_data = {
        'goods_nomenclature': pd.DataFrame({
            'goods_code': ['61102000', '61103000', 'invalid'],
            'description': ['Cotton hoodies', 'Synthetic hoodies', ''],
            'level': [6, 6, 6]
        }),
        'measures': pd.DataFrame({
            'goods_code': ['61102000', '61103000'],
            'measure_type': ['import', 'export'],
            'duty_components': ['12.5%', 'EUR 2.50/100kg']
        })
    }
    
    report = validate_staging_data(test_data)
    print("Validation Report:")
    print(report)
