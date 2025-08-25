# WORKFLOW: Transform staging data to canonical database schema.
# Used by: ETL pipeline, database population, data transformation
# Functions:
# 1. transform_goods_nomenclature() - Transform HS codes and descriptions
# 2. transform_measures() - Transform import/export measures and duties
# 3. transform_geographies() - Transform country codes and groupings
# 4. transform_vat_rates() - Transform VAT rate data
# 5. transform_legal_bases() - Transform legal regulation data
# 6. load_canonical_data() - Load transformed data into canonical tables
#
# Transform flow: Staging data -> Schema mapping -> Data transformation -> Canonical tables
# This ensures all data conforms to the canonical schema for consistent API responses.

"""
Transform staging data to canonical database schema.
"""

import pandas as pd
import logging
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from datetime import datetime
from db.models import (
    GoodsNomenclature, MeasuresImport, MeasuresExport, Geographies,
    VatRates, LegalBases, Footnotes, Box44, ExchangeRates, ReachMap
)
from etl.duty_parser import parse_duty_components

logger = logging.getLogger(__name__)


def transform_goods_nomenclature(staging_data: Dict[str, pd.DataFrame]) -> List[GoodsNomenclature]:
    """
    Transform HS codes and descriptions to canonical format.
    
    Args:
        staging_data: Dictionary of staging DataFrames
        
    Returns:
        List of GoodsNomenclature objects
    """
    nomenclature_items = []
    
    # Look for goods nomenclature data in staging
    for key, df in staging_data.items():
        if 'goods' in key.lower() or 'nomenclature' in key.lower():
            try:
                for _, row in df.iterrows():
                    item = GoodsNomenclature(
                        goods_code=str(row.get('goods_code', '')),
                        description=str(row.get('description', '')),
                        level=int(row.get('level', 0)),
                        valid_from=row.get('valid_from', datetime.now()),
                        valid_to=row.get('valid_to'),
                        is_leaf=bool(row.get('is_leaf', False))
                    )
                    nomenclature_items.append(item)
                    
                logger.info(f"Transformed {len(nomenclature_items)} goods nomenclature items from {key}")
                
            except Exception as e:
                logger.error(f"Failed to transform goods nomenclature from {key}: {e}")
                continue
    
    return nomenclature_items


def transform_measures(staging_data: Dict[str, pd.DataFrame]) -> tuple[List[MeasuresImport], List[MeasuresExport]]:
    """
    Transform import/export measures to canonical format.
    
    Args:
        staging_data: Dictionary of staging DataFrames
        
    Returns:
        Tuple of (import_measures, export_measures)
    """
    import_measures = []
    export_measures = []
    
    for key, df in staging_data.items():
        if 'measure' in key.lower():
            try:
                for _, row in df.iterrows():
                    # Parse duty components
                    duty_components = parse_duty_components(str(row.get('duty_components', '')))
                    
                    measure_data = {
                        'goods_code': str(row.get('goods_code', '')),
                        'measure_type': str(row.get('measure_type', '')),
                        'duty_components': duty_components,
                        'legal_base_id': str(row.get('legal_base_id', '')),
                        'legal_base_title': str(row.get('legal_base_title', '')),
                        'valid_from': row.get('valid_from', datetime.now()),
                        'valid_to': row.get('valid_to'),
                        'footnote_code': str(row.get('footnote_code', '')) if pd.notna(row.get('footnote_code')) else None,
                        'cond_cert_code': str(row.get('cond_cert_code', '')) if pd.notna(row.get('cond_cert_code')) else None
                    }
                    
                    if 'import' in key.lower():
                        measure = MeasuresImport(
                            origin_group=str(row.get('origin_group', '')),
                            **measure_data
                        )
                        import_measures.append(measure)
                    elif 'export' in key.lower():
                        measure = MeasuresExport(
                            destination_group=str(row.get('destination_group', '')),
                            **measure_data
                        )
                        export_measures.append(measure)
                        
            except Exception as e:
                logger.error(f"Failed to transform measures from {key}: {e}")
                continue
    
    logger.info(f"Transformed {len(import_measures)} import measures and {len(export_measures)} export measures")
    return import_measures, export_measures


def transform_geographies(staging_data: Dict[str, pd.DataFrame]) -> List[Geographies]:
    """
    Transform geography data to canonical format.
    
    Args:
        staging_data: Dictionary of staging DataFrames
        
    Returns:
        List of Geographies objects
    """
    geographies = []
    
    for key, df in staging_data.items():
        if 'geo' in key.lower() or 'country' in key.lower():
            try:
                for _, row in df.iterrows():
                    geo = Geographies(
                        code=str(row.get('code', '')),
                        type=str(row.get('type', '')),
                        name=str(row.get('name', '')),
                        group_name=str(row.get('group_name', '')) if pd.notna(row.get('group_name')) else None
                    )
                    geographies.append(geo)
                    
                logger.info(f"Transformed {len(geographies)} geography items from {key}")
                
            except Exception as e:
                logger.error(f"Failed to transform geographies from {key}: {e}")
                continue
    
    return geographies


def transform_vat_rates(staging_data: Dict[str, pd.DataFrame]) -> List[VatRates]:
    """
    Transform VAT rate data to canonical format.
    
    Args:
        staging_data: Dictionary of staging DataFrames
        
    Returns:
        List of VatRates objects
    """
    vat_rates = []
    
    for key, df in staging_data.items():
        if 'vat' in key.lower():
            try:
                for _, row in df.iterrows():
                    vat_rate = VatRates(
                        country_code=str(row.get('country_code', '')),
                        standard_rate=float(row.get('standard_rate', 0.0)),
                        reduced_rate_1=float(row.get('reduced_rate_1', 0.0)) if pd.notna(row.get('reduced_rate_1')) else None,
                        valid_from=row.get('valid_from', datetime.now()),
                        valid_to=row.get('valid_to')
                    )
                    vat_rates.append(vat_rate)
                    
                logger.info(f"Transformed {len(vat_rates)} VAT rates from {key}")
                
            except Exception as e:
                logger.error(f"Failed to transform VAT rates from {key}: {e}")
                continue
    
    return vat_rates


def transform_legal_bases(staging_data: Dict[str, pd.DataFrame]) -> List[LegalBases]:
    """
    Transform legal bases data to canonical format.
    
    Args:
        staging_data: Dictionary of staging DataFrames
        
    Returns:
        List of LegalBases objects
    """
    legal_bases = []
    
    for key, df in staging_data.items():
        if 'legal' in key.lower() or 'regulation' in key.lower():
            try:
                for _, row in df.iterrows():
                    legal_base = LegalBases(
                        id=str(row.get('id', '')),
                        title=str(row.get('title', ''))
                    )
                    legal_bases.append(legal_base)
                    
                logger.info(f"Transformed {len(legal_bases)} legal bases from {key}")
                
            except Exception as e:
                logger.error(f"Failed to transform legal bases from {key}: {e}")
                continue
    
    return legal_bases


def load_canonical_data(transformed_data: Dict[str, List], db: Session) -> None:
    """
    Load transformed data into canonical tables.
    
    Args:
        transformed_data: Dictionary of transformed data objects
        db: Database session
    """
    try:
        # Load goods nomenclature
        if 'goods_nomenclature' in transformed_data:
            db.add_all(transformed_data['goods_nomenclature'])
            logger.info(f"Loaded {len(transformed_data['goods_nomenclature'])} goods nomenclature items")
        
        # Load import measures
        if 'import_measures' in transformed_data:
            db.add_all(transformed_data['import_measures'])
            logger.info(f"Loaded {len(transformed_data['import_measures'])} import measures")
        
        # Load export measures
        if 'export_measures' in transformed_data:
            db.add_all(transformed_data['export_measures'])
            logger.info(f"Loaded {len(transformed_data['export_measures'])} export measures")
        
        # Load geographies
        if 'geographies' in transformed_data:
            db.add_all(transformed_data['geographies'])
            logger.info(f"Loaded {len(transformed_data['geographies'])} geography items")
        
        # Load VAT rates
        if 'vat_rates' in transformed_data:
            db.add_all(transformed_data['vat_rates'])
            logger.info(f"Loaded {len(transformed_data['vat_rates'])} VAT rates")
        
        # Load legal bases
        if 'legal_bases' in transformed_data:
            db.add_all(transformed_data['legal_bases'])
            logger.info(f"Loaded {len(transformed_data['legal_bases'])} legal bases")
        
        db.commit()
        logger.info("Successfully loaded all canonical data")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to load canonical data: {e}")
        raise


def main(staging_data: Dict[str, pd.DataFrame], db: Session) -> None:
    """
    Main transformation function.
    
    Args:
        staging_data: Dictionary of staging DataFrames
        db: Database session
    """
    try:
        logger.info("Starting transformation of staging data to canonical schema")
        
        # Transform data
        transformed_data = {}
        
        transformed_data['goods_nomenclature'] = transform_goods_nomenclature(staging_data)
        import_measures, export_measures = transform_measures(staging_data)
        transformed_data['import_measures'] = import_measures
        transformed_data['export_measures'] = export_measures
        transformed_data['geographies'] = transform_geographies(staging_data)
        transformed_data['vat_rates'] = transform_vat_rates(staging_data)
        transformed_data['legal_bases'] = transform_legal_bases(staging_data)
        
        # Load into canonical tables
        load_canonical_data(transformed_data, db)
        
        logger.info("Successfully transformed and loaded canonical data")
        
    except Exception as e:
        logger.error(f"Transformation failed: {e}")
        raise


if __name__ == "__main__":
    # This would be called from the ETL pipeline
    pass
