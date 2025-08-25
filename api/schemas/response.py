# WORKFLOW: Pydantic response schemas that match the JSON Schema specification.
# Used by: API response generation, deterministic builder, testing
# Schemas include:
# 1. TradeComplianceResponse - Main response structure
# 2. DeterministicValues - Database-derived values
# 3. ImportMeasure/ExportMeasure - Trade measures with duty components
# 4. VatRate/ExchangeRate - Financial data
# 5. AnnotationsLLM - LLM-generated explanations with guardrails
# 6. Completeness/Unknowns - Data quality indicators
#
# Response flow: Database query -> Pydantic model -> JSON Schema validation -> API response
# Ensures all responses conform to the strict schema requirements.

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union, Dict, Any
from datetime import date, datetime
from enum import Enum


class DutyType(str, Enum):
    AD_VALOREM = "ad_valorem"
    SPECIFIC = "specific"
    COMPOUND = "compound"


class DutyUnit(str, Enum):
    PERCENT = "percent"
    EUR_PER_100KG = "eur/100kg"
    EUR_PER_UNIT = "eur/unit"
    MIXED = "mixed"


class ClassificationMethod(str, Enum):
    RETRIEVAL_RERANK_CALIBRATE = "retrieval_rerank_calibrate"
    PROVIDED_BY_USER = "provided_by_user"


class QueryMeta(BaseModel):
    query_date: Optional[date] = None


class QueryParameters(BaseModel):
    hs_code: str = Field(..., pattern=r"^[0-9]{4,10}$")
    origin: str = Field(..., min_length=2, max_length=3)
    destination: str = Field(..., min_length=2, max_length=3)
    product_description: Optional[str] = None
    incoterm: Optional[str] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)


class ClassificationMeta(BaseModel):
    method: Optional[ClassificationMethod] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    abstained: Optional[bool] = None


class Metadata(BaseModel):
    source_system: Optional[str] = None
    dataset_version: Optional[str] = None
    last_updated: Optional[date] = None


class GoodsNomenclatureItem(BaseModel):
    goods_code: str
    description: str
    level: int
    validity_start_date: date
    validity_end_date: Optional[date] = None
    is_leaf: bool


class DutyComponent(BaseModel):
    type: DutyType
    value: float
    unit: DutyUnit


class Applicability(BaseModel):
    valid_from: date
    valid_to: Optional[date] = None


class LegalBase(BaseModel):
    id: str
    title: str


class ImportMeasure(BaseModel):
    goods_code: str
    origin_group: str
    measure_type: str
    duty_components: List[DutyComponent] = Field(..., min_items=1)
    preference_scheme: Optional[str] = None
    rules_of_origin: Optional[str] = None
    applicability: Applicability
    legal_base: LegalBase
    footnote_code: Optional[str] = None
    cond_cert_code: Optional[str] = None


class ExportMeasure(BaseModel):
    goods_code: str
    destination_group: str
    measure_type: str
    duty_components: List[DutyComponent] = Field(..., min_items=1)
    applicability: Applicability
    legal_base: LegalBase
    footnote_code: Optional[str] = None
    cond_cert_code: Optional[str] = None


class ApplicableRateResolution(BaseModel):
    preference_possible: Optional[bool] = None
    required_proof: Optional[str] = None
    chosen_measure_origin: Optional[str] = None
    chosen_duty_rate_percent: Optional[float] = None
    fallback_if_no_proof_percent: Optional[float] = None


class MeasureCondition(BaseModel):
    certificate_code: str
    box44_codes: Optional[List[str]] = None
    action: str
    threshold_value: Optional[float] = None
    threshold_unit: Optional[str] = None
    notes: Optional[str] = None


class CertificateDocument(BaseModel):
    name: str
    issuer: Optional[str] = None
    mandatory_if: str
    fields: Optional[Dict[str, str]] = None


class ProductSafetyFramework(BaseModel):
    regulation: str
    applies: bool
    notes: Optional[List[str]] = None


class ReachRestriction(BaseModel):
    entry: int
    substance_scope: Optional[str] = None
    limit: Optional[str] = None
    article_relevance: Optional[str] = None
    required: Union[bool, str]


class ToyPathConditional(BaseModel):
    trigger: Optional[str] = None
    directive: Optional[str] = None
    standards: Optional[List[str]] = None
    marking: Optional[List[str]] = None


class ComplianceRequirements(BaseModel):
    product_safety_framework: Optional[List[ProductSafetyFramework]] = None
    reach_restrictions_annex_xvii: Optional[List[ReachRestriction]] = None
    toy_path_conditional: Optional[ToyPathConditional] = None
    labelling: Optional[List[str]] = None


class RecommendedTestMethod(BaseModel):
    purpose: str
    method: str
    acceptance: Optional[str] = None


class SpecialMeasures(BaseModel):
    quotas: Optional[str] = None
    anti_dumping: Optional[str] = None
    countervailing: Optional[str] = None
    safeguards: Optional[str] = None
    suspensions: Optional[str] = None


class GeographicalArea(BaseModel):
    member_country: str
    country_group: Optional[str] = None
    description: Optional[str] = None


class VatRate(BaseModel):
    country: str
    standard_rate_percent: float
    reduced_rate_1_percent: Optional[float] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class ExchangeRate(BaseModel):
    iso: str
    rate: float
    rate_date: date
    source: str


class Provenance(BaseModel):
    legal_bases: List[LegalBase] = Field(..., min_items=1)


class Completeness(BaseModel):
    has_reach_mapping: Optional[bool] = None
    has_test_methods: Optional[bool] = None
    all_measures_have_legal_base: Optional[bool] = None
    all_required_vat_present: Optional[bool] = None


class Unknown(BaseModel):
    field: str
    reason: str


class DeterministicValues(BaseModel):
    metadata: Optional[Metadata] = None
    goods_nomenclature_en: List[GoodsNomenclatureItem] = Field(..., min_items=1)
    import_measures: List[ImportMeasure] = Field(..., min_items=1)
    export_measures: Optional[List[ExportMeasure]] = None
    applicable_rate_resolution: Optional[ApplicableRateResolution] = None
    measure_conditions: Optional[List[MeasureCondition]] = None
    certificates_and_documents: Optional[List[CertificateDocument]] = None
    compliance_requirements: Optional[ComplianceRequirements] = None
    recommended_test_methods: Optional[List[RecommendedTestMethod]] = None
    special_measures: Optional[SpecialMeasures] = None
    geographical_areas_origin: Optional[List[GeographicalArea]] = None
    geographical_areas_destination: Optional[List[GeographicalArea]] = None
    vat_rates: List[VatRate] = Field(..., min_items=1)
    exchange_rates: Optional[List[ExchangeRate]] = None
    provenance: Provenance
    completeness: Optional[Completeness] = None
    unknowns: Optional[List[Unknown]] = None
    flags: Optional[List[str]] = None


class CertificateExplanation(BaseModel):
    code: str
    what_it_is: str
    when_required: str
    issuer: str
    note: Optional[str] = None


class SafetyInfo(BaseModel):
    hallucination_guard: bool
    disclaimer: str


class AnnotationsLLM(BaseModel):
    human_summary: Optional[str] = None
    certificate_explanations: Optional[List[CertificateExplanation]] = None
    compliance_notes: Optional[List[str]] = None
    safety: Optional[SafetyInfo] = None


class TradeComplianceResponse(BaseModel):
    query_meta: Optional[QueryMeta] = None
    query_parameters: QueryParameters
    classification_meta: Optional[ClassificationMeta] = None
    deterministic_values: DeterministicValues
    annotations_llm: Optional[AnnotationsLLM] = None

    class Config:
        json_schema_extra = {
            "example": {
                "query_parameters": {
                    "hs_code": "61102000",
                    "origin": "PK",
                    "destination": "DE",
                    "product_description": "cotton hoodies"
                },
                "deterministic_values": {
                    "goods_nomenclature_en": [
                        {
                            "goods_code": "61102000",
                            "description": "Jerseys, pullovers, cardigans, waistcoats and similar articles, knitted or crocheted, of cotton",
                            "level": 8,
                            "validity_start_date": "2023-01-01",
                            "is_leaf": True
                        }
                    ],
                    "import_measures": [
                        {
                            "goods_code": "61102000",
                            "origin_group": "ERGA OMNES",
                            "measure_type": "103",
                            "duty_components": [
                                {
                                    "type": "ad_valorem",
                                    "value": 12.0,
                                    "unit": "percent"
                                }
                            ],
                            "applicability": {
                                "valid_from": "2023-01-01"
                            },
                            "legal_base": {
                                "id": "32022R1234",
                                "title": "Commission Implementing Regulation (EU) 2022/1234"
                            }
                        }
                    ],
                    "vat_rates": [
                        {
                            "country": "DE",
                            "standard_rate_percent": 19.0
                        }
                    ],
                    "provenance": {
                        "legal_bases": [
                            {
                                "id": "32022R1234",
                                "title": "Commission Implementing Regulation (EU) 2022/1234"
                            }
                        ]
                    }
                }
            }
        }
