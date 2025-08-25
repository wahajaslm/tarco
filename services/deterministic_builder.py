# WORKFLOW: Deterministic JSON builder that assembles responses from database data only.
# Used by: Deterministic endpoints, chat endpoints, response generation
# Functions:
# 1. build_response() - Build complete TradeComplianceResponse from database
# 2. _build_deterministic_values() - Assemble all deterministic data
# 3. _get_import_measures() - Get import duties and measures
# 4. _resolve_applicable_rate() - Determine applicable duty rate
# 5. _assess_completeness() - Check data quality and identify unknowns
#
# Builder flow: HS code + origin/destination -> Database queries -> Pydantic models -> Response
# This ensures ALL numeric values come from the database, never from LLM
# Enforces the strict boundary: database = facts, LLM = explanations only

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from db.models import (
    GoodsNomenclature, MeasuresImport, MeasuresExport, MeasureConditions,
    VatRates, ExchangeRates, ReachMap
)
# Import Pydantic models inside methods to avoid circular imports
# from api.schemas.response import (
#     TradeComplianceResponse, QueryParameters, DeterministicValues,
#     ImportMeasure, ExportMeasure, DutyComponent,
#     Applicability, LegalBase, VatRate, ExchangeRate, Provenance,
#     ApplicableRateResolution, MeasureCondition, Completeness, Unknown
# )
import logging

logger = logging.getLogger(__name__)


class DeterministicBuilder:
    """Builds deterministic JSON responses from database data only."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def build_response(self, hs_code: str, origin: str, destination: str, 
                      product_description: Optional[str] = None):
        """
        Build complete trade compliance response from database.
        
        Args:
            hs_code: HS code
            origin: Origin country code
            destination: Destination country code
            product_description: Optional product description
            
        Returns:
            TradeComplianceResponse with all deterministic values
        """
        try:
            logger.info(f"Building deterministic response for HS: {hs_code}, Origin: {origin}, Dest: {destination}")
            
            # Test database connection first
            logger.info("Testing database connection...")
            from sqlalchemy import text
            test_query = self.db.execute(text("SELECT 1")).fetchone()
            logger.info(f"Database connection test result: {test_query}")
            
            # Import Pydantic models
            from api.schemas.response import TradeComplianceResponse, QueryParameters
            
            # Build query parameters
            logger.info("Creating QueryParameters...")
            try:
                query_params = QueryParameters(
                    hs_code=hs_code,
                    origin=origin,
                    destination=destination,
                    product_description=product_description
                )
                logger.info("QueryParameters created successfully")
            except Exception as e:
                logger.error(f"Error creating QueryParameters: {e}")
                raise
            
            # Build deterministic values
            logger.info("Starting to build deterministic values...")
            logger.info("About to call _build_deterministic_values...")
            try:
                deterministic_values = self._build_deterministic_values(hs_code, origin, destination)
                logger.info("Deterministic values built successfully")
            except Exception as e:
                logger.error(f"Error in _build_deterministic_values: {e}")
                raise
            
            # Create response
            response = TradeComplianceResponse(
                query_parameters=query_params,
                deterministic_values=deterministic_values
            )
            
            logger.info("Deterministic response built successfully")
            return response
            
        except Exception as e:
            logger.error(f"Failed to build deterministic response: {e}")
            raise
    
    def _build_deterministic_values(self, hs_code: str, origin: str, destination: str):
        """Build deterministic values from database."""
        try:
            # Import Pydantic models
            from api.schemas.response import (  # noqa: F401
                DeterministicValues, VatRate, ExchangeRate, MeasureCondition,
                ApplicableRateResolution, Completeness, Unknown, Provenance
            )
            
            logger.info("Starting _build_deterministic_values...")
            
            # Get goods nomenclature
            logger.info("Getting goods nomenclature...")
            goods_nomenclature = self._get_goods_nomenclature(hs_code)
            logger.info(f"Got {len(goods_nomenclature)} nomenclature items")
            
            # Get import measures
            import_measures = self._get_import_measures(hs_code, origin)
            
            # Get export measures
            export_measures = self._get_export_measures(hs_code, destination)
            
            # Get VAT rates
            vat_rates = self._get_vat_rates(destination)
            
            # Get exchange rates
            exchange_rates = self._get_exchange_rates()
            
            # Get measure conditions
            measure_conditions = self._get_measure_conditions(hs_code)
            
            # Get applicable rate resolution
            applicable_rate_resolution = self._resolve_applicable_rate(import_measures, origin)
            
            # Get completeness and unknowns
            completeness, unknowns = self._assess_completeness(
                hs_code, import_measures, export_measures, vat_rates
            )
            
            # Get provenance
            provenance = self._get_provenance(import_measures, export_measures)
            
            return DeterministicValues(
                goods_nomenclature_en=goods_nomenclature,
                import_measures=import_measures,
                export_measures=export_measures,
                vat_rates=vat_rates,
                exchange_rates=exchange_rates,
                measure_conditions=measure_conditions,
                applicable_rate_resolution=applicable_rate_resolution,
                completeness=completeness,
                unknowns=unknowns,
                provenance=provenance
            )
            
        except Exception as e:
            logger.error(f"Failed to build deterministic values: {e}")
            raise
    
    def _get_goods_nomenclature(self, hs_code: str) -> List[Any]:
        """Get goods nomenclature for HS code."""
        try:
            # Import the correct type
            from api.schemas.response import GoodsNomenclatureItem
            
            # Get the specific HS code and its parent levels
            nomenclature_items = []
            
            # Start with the full HS code and work backwards
            current_code = hs_code
            while len(current_code) >= 4:
                item = self.db.query(GoodsNomenclature).filter(
                    GoodsNomenclature.goods_code == current_code
                ).first()

                if item:
                    nomenclature_items.append(GoodsNomenclatureItem(
                        goods_code=item.goods_code,
                        description=item.description,
                        level=item.level,
                        validity_start_date=item.valid_from.date(),
                        validity_end_date=item.valid_to.date() if item.valid_to else None,
                        is_leaf=item.is_leaf
                    ))

                if len(current_code) <= 4:
                    break
                current_code = current_code[:-2]
            
            return nomenclature_items
            
        except Exception as e:
            logger.error(f"Failed to get goods nomenclature: {e}")
            return []
    
    def _get_import_measures(self, hs_code: str, origin: str) -> List[Any]:
        """Get import measures for HS code and origin."""
        try:
            # Import the correct types
            from api.schemas.response import ImportMeasure, Applicability, LegalBase
            # Get measures for the specific HS code
            measures = self.db.query(MeasuresImport).filter(
                and_(
                    MeasuresImport.goods_code == hs_code,
                    or_(
                        MeasuresImport.origin_group == "ERGA OMNES",
                        MeasuresImport.origin_group == origin
                    )
                )
            ).all()
            
            import_measures = []
            for measure in measures:
                # Parse duty components
                duty_components = self._parse_duty_components(measure.duty_components)
                
                import_measures.append(ImportMeasure(
                    goods_code=measure.goods_code,
                    origin_group=measure.origin_group,
                    measure_type=measure.measure_type,
                    duty_components=duty_components,
                    applicability=Applicability(
                        valid_from=measure.valid_from.date(),
                        valid_to=measure.valid_to.date() if measure.valid_to else None
                    ),
                    legal_base=LegalBase(
                        id=measure.legal_base_id,
                        title=measure.legal_base_title
                    ),
                    footnote_code=measure.footnote_code,
                    cond_cert_code=measure.cond_cert_code
                ))
            
            return import_measures
            
        except Exception as e:
            logger.error(f"Failed to get import measures: {e}")
            return []
    
    def _get_export_measures(self, hs_code: str, destination: str) -> List[Any]:
        """Get export measures for HS code and destination."""
        try:
            # Import the correct types
            from api.schemas.response import ExportMeasure, Applicability, LegalBase
            measures = self.db.query(MeasuresExport).filter(
                and_(
                    MeasuresExport.goods_code == hs_code,
                    MeasuresExport.destination_group == destination
                )
            ).all()
            
            export_measures = []
            for measure in measures:
                duty_components = self._parse_duty_components(measure.duty_components)
                
                export_measures.append(ExportMeasure(
                    goods_code=measure.goods_code,
                    destination_group=measure.destination_group,
                    measure_type=measure.measure_type,
                    duty_components=duty_components,
                    applicability=Applicability(
                        valid_from=measure.valid_from.date(),
                        valid_to=measure.valid_to.date() if measure.valid_to else None
                    ),
                    legal_base=LegalBase(
                        id=measure.legal_base_id,
                        title=measure.legal_base_title
                    ),
                    footnote_code=measure.footnote_code,
                    cond_cert_code=measure.cond_cert_code
                ))
            
            return export_measures
            
        except Exception as e:
            logger.error(f"Failed to get export measures: {e}")
            return []
    
    def _parse_duty_components(self, duty_components_json: Dict) -> List[Any]:
        """Parse duty components from JSONB."""
        try:
            # Import the correct type
            from api.schemas.response import DutyComponent
            components = []
            
            if isinstance(duty_components_json, list):
                for comp in duty_components_json:
                    components.append(DutyComponent(
                        type=comp.get('type', 'ad_valorem'),
                        value=float(comp.get('value', 0)),
                        unit=comp.get('unit', 'percent')
                    ))
            else:
                # Handle single component
                components.append(DutyComponent(
                    type=duty_components_json.get('type', 'ad_valorem'),
                    value=float(duty_components_json.get('value', 0)),
                    unit=duty_components_json.get('unit', 'percent')
                ))
            
            return components
            
        except Exception as e:
            logger.error(f"Failed to parse duty components: {e}")
            return []
    
    def _get_vat_rates(self, country: str) -> List[Any]:
        """Get VAT rates for destination country."""
        try:
            # Import the correct type
            from api.schemas.response import VatRate
            vat_rates = self.db.query(VatRates).filter(
                VatRates.country_code == country
            ).all()
            
            return [
                VatRate(
                    country=rate.country_code,
                    standard_rate_percent=rate.standard_rate,
                    reduced_rate_1_percent=rate.reduced_rate_1,
                    valid_from=rate.valid_from.date() if rate.valid_from else None,
                    valid_to=rate.valid_to.date() if rate.valid_to else None
                )
                for rate in vat_rates
            ]
            
        except Exception as e:
            logger.error(f"Failed to get VAT rates: {e}")
            return []
    
    def _get_exchange_rates(self) -> List[Any]:
        """Get current exchange rates."""
        try:
            # Import the correct type
            from api.schemas.response import ExchangeRate
            # Get latest exchange rates for major currencies
            currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF']
            exchange_rates = []
            
            for currency in currencies:
                rate = self.db.query(ExchangeRates).filter(
                    ExchangeRates.iso == currency
                ).order_by(ExchangeRates.rate_date.desc()).first()
                
                if rate:
                    exchange_rates.append(ExchangeRate(
                        iso=rate.iso,
                        rate=rate.rate,
                        rate_date=rate.rate_date.date(),
                        source=rate.source
                    ))
            
            return exchange_rates
            
        except Exception as e:
            logger.error(f"Failed to get exchange rates: {e}")
            return []
    
    def _get_measure_conditions(self, hs_code: str) -> List[Any]:
        """Get measure conditions for HS code."""
        try:
            # Import the correct type
            from api.schemas.response import MeasureCondition
            conditions = self.db.query(MeasureConditions).filter(
                MeasureConditions.goods_code == hs_code
            ).all()
            
            return [
                MeasureCondition(
                    certificate_code=condition.certificate_code,
                    action=condition.action,
                    threshold_value=condition.threshold_value,
                    threshold_unit=condition.threshold_unit,
                    notes=condition.notes,
                    box44_codes=condition.box44_codes
                )
                for condition in conditions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get measure conditions: {e}")
            return []
    
    def _resolve_applicable_rate(self, import_measures: List[Any], origin: str) -> Optional[Any]:
        """Resolve applicable duty rate."""
        try:
            # Import the correct type
            from api.schemas.response import ApplicableRateResolution
            if not import_measures:
                return None
            
            # Find preferential rate if available
            preferential_measure = None
            erga_omnes_measure = None
            
            for measure in import_measures:
                if measure.origin_group == origin:
                    preferential_measure = measure
                elif measure.origin_group == "ERGA OMNES":
                    erga_omnes_measure = measure
            
            # Determine applicable rate
            if preferential_measure:
                duty_rate = self._extract_duty_rate(preferential_measure.duty_components)
                return ApplicableRateResolution(
                    preference_possible=True,
                    required_proof=preferential_measure.cond_cert_code,
                    chosen_measure_origin=origin,
                    chosen_duty_rate_percent=duty_rate,
                    fallback_if_no_proof_percent=self._extract_duty_rate(erga_omnes_measure.duty_components) if erga_omnes_measure else None
                )
            elif erga_omnes_measure:
                duty_rate = self._extract_duty_rate(erga_omnes_measure.duty_components)
                return ApplicableRateResolution(
                    preference_possible=False,
                    chosen_measure_origin="ERGA OMNES",
                    chosen_duty_rate_percent=duty_rate
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to resolve applicable rate: {e}")
            return None
    
    def _extract_duty_rate(self, duty_components: List[Any]) -> Optional[float]:
        """Extract duty rate percentage from duty components."""
        try:
            for component in duty_components:
                if component.type == "ad_valorem" and component.unit == "percent":
                    return component.value
            return None
        except Exception as e:
            logger.error(f"Failed to extract duty rate: {e}")
            return None
    
    def _assess_completeness(self, hs_code: str, import_measures: List[Any],
                           export_measures: List[Any], vat_rates: List[Any]) -> Tuple[Any, List[Any]]:
        """Assess completeness and identify unknowns."""
        try:
            # Import the correct types
            from api.schemas.response import Completeness, Unknown
            completeness = Completeness()
            unknowns = []
            
            # Check if all measures have legal base
            all_measures = import_measures + export_measures
            completeness.all_measures_have_legal_base = all(
                measure.legal_base.id and measure.legal_base.title 
                for measure in all_measures
            )
            
            if not completeness.all_measures_have_legal_base:
                unknowns.append(Unknown(
                    field="legal_base",
                    reason="Some measures missing legal base information"
                ))
            
            # Check VAT rates
            completeness.all_required_vat_present = len(vat_rates) > 0
            
            if not completeness.all_required_vat_present:
                unknowns.append(Unknown(
                    field="vat_rates",
                    reason="No VAT rates found for destination country"
                ))
            
            # Check REACH mapping
            reach_mapping = self.db.query(ReachMap).filter(
                ReachMap.goods_code_prefix == hs_code[:6]
            ).first()
            completeness.has_reach_mapping = reach_mapping is not None
            
            if not completeness.has_reach_mapping:
                unknowns.append(Unknown(
                    field="reach_mapping",
                    reason="No REACH mapping found for HS code prefix"
                ))
            
            return completeness, unknowns
            
        except Exception as e:
            logger.error(f"Failed to assess completeness: {e}")
            return Completeness(), []
    
    def _get_provenance(self, import_measures: List[Any], 
                       export_measures: List[Any]) -> Any:
        """Get legal bases for provenance."""
        try:
            from api.schemas.response import Provenance, LegalBase

            legal_bases: List[LegalBase] = []
            seen_bases = set()

            for measure in import_measures + export_measures:
                base = getattr(measure, "legal_base", None)
                if base is None and isinstance(measure, dict):
                    base = measure.get("legal_base")
                if not base:
                    continue

                base_id = getattr(base, "id", None) or (base.get("id") if isinstance(base, dict) else None)
                title = getattr(base, "title", None) or (base.get("title") if isinstance(base, dict) else None)

                if base_id and base_id not in seen_bases:
                    legal_bases.append(LegalBase(id=base_id, title=title or ""))
                    seen_bases.add(base_id)

            return Provenance(legal_bases=legal_bases)

        except Exception as e:
            logger.error(f"Failed to get provenance: {e}")
            return Provenance()


# Factory function
def create_deterministic_builder(db: Session) -> DeterministicBuilder:
    """Create deterministic builder instance."""
    return DeterministicBuilder(db)
