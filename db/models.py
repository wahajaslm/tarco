# WORKFLOW: Database models for the canonical Trade Compliance schema.
# Used by: ETL processes, API endpoints, deterministic builder
# Models represent:
# 1. goods_nomenclature - HS code hierarchy and descriptions
# 2. measures_import/export - Duty rates and trade measures
# 3. measure_conditions - Certificate requirements and conditions
# 4. geographies - Country codes and groupings
# 5. vat_rates - VAT rates by country
# 6. legal_bases - Legal regulations and sources
# 7. reach_map - REACH compliance mappings
# 8. text_index schema - Vector embeddings for RAG
#
# Data flow: XLSX -> ETL -> Staging -> Canonical models -> API responses

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class GoodsNomenclature(Base):
    __tablename__ = "goods_nomenclature"
    
    goods_code = Column(String(10), primary_key=True, index=True)
    description = Column(Text, nullable=False)
    level = Column(Integer, nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=True)
    is_leaf = Column(Boolean, default=False)
    
    # Relationships
    import_measures = relationship("MeasuresImport", back_populates="goods_nomenclature")
    export_measures = relationship("MeasuresExport", back_populates="goods_nomenclature")
    measure_conditions = relationship("MeasureConditions", back_populates="goods_nomenclature")
    
    __table_args__ = (
        Index('idx_goods_code_level', 'goods_code', 'level'),
        Index('idx_is_leaf', 'is_leaf'),
    )


class MeasuresImport(Base):
    __tablename__ = "measures_import"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    goods_code = Column(String(10), ForeignKey("goods_nomenclature.goods_code"), nullable=False)
    origin_group = Column(String(50), nullable=False)
    measure_type = Column(String(10), nullable=False)
    duty_components = Column(JSON, nullable=False)  # Array of duty components
    legal_base_id = Column(String(50), nullable=False)
    legal_base_title = Column(Text, nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=True)
    footnote_code = Column(String(10), nullable=True)
    cond_cert_code = Column(String(10), nullable=True)
    
    # Relationships
    goods_nomenclature = relationship("GoodsNomenclature", back_populates="import_measures")
    
    __table_args__ = (
        Index('idx_import_goods_origin', 'goods_code', 'origin_group'),
        Index('idx_import_legal_base', 'legal_base_id'),
        Index('idx_import_validity', 'valid_from', 'valid_to'),
    )


class MeasuresExport(Base):
    __tablename__ = "measures_export"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    goods_code = Column(String(10), ForeignKey("goods_nomenclature.goods_code"), nullable=False)
    destination_group = Column(String(50), nullable=False)
    measure_type = Column(String(10), nullable=False)
    duty_components = Column(JSON, nullable=False)  # Array of duty components
    legal_base_id = Column(String(50), nullable=False)
    legal_base_title = Column(Text, nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=True)
    footnote_code = Column(String(10), nullable=True)
    cond_cert_code = Column(String(10), nullable=True)
    
    # Relationships
    goods_nomenclature = relationship("GoodsNomenclature", back_populates="export_measures")
    
    __table_args__ = (
        Index('idx_export_goods_dest', 'goods_code', 'destination_group'),
        Index('idx_export_legal_base', 'legal_base_id'),
        Index('idx_export_validity', 'valid_from', 'valid_to'),
    )


class MeasureConditions(Base):
    __tablename__ = "measure_conditions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    goods_code = Column(String(10), ForeignKey("goods_nomenclature.goods_code"), nullable=False)
    certificate_code = Column(String(10), nullable=False)
    action = Column(String(50), nullable=False)
    threshold_value = Column(Float, nullable=True)
    threshold_unit = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    box44_codes = Column(JSON, nullable=True)  # Array of box44 codes
    
    # Relationships
    goods_nomenclature = relationship("GoodsNomenclature", back_populates="measure_conditions")
    
    __table_args__ = (
        Index('idx_conditions_goods_cert', 'goods_code', 'certificate_code'),
    )


class Geographies(Base):
    __tablename__ = "geographies"
    
    code = Column(String(10), primary_key=True)
    type = Column(String(20), nullable=False)  # country, group, etc.
    name = Column(String(100), nullable=False)
    group_name = Column(String(50), nullable=True)  # ERGA OMNES, GSP, EU, etc.
    
    __table_args__ = (
        Index('idx_geo_type', 'type'),
        Index('idx_geo_group', 'group_name'),
    )


class VatRates(Base):
    __tablename__ = "vat_rates"
    
    country_code = Column(String(3), primary_key=True)
    standard_rate = Column(Float, nullable=False)
    reduced_rate_1 = Column(Float, nullable=True)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_vat_validity', 'valid_from', 'valid_to'),
    )


class Footnotes(Base):
    __tablename__ = "footnotes"
    
    code = Column(String(10), primary_key=True)
    description = Column(Text, nullable=False)


class Box44(Base):
    __tablename__ = "box44"
    
    code = Column(String(10), primary_key=True)
    description = Column(Text, nullable=False)


class ExchangeRates(Base):
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    iso = Column(String(3), nullable=False)
    rate = Column(Float, nullable=False)
    rate_date = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=False)
    
    __table_args__ = (
        Index('idx_exchange_iso_date', 'iso', 'rate_date'),
    )


class LegalBases(Base):
    __tablename__ = "legal_bases"
    
    id = Column(String(50), primary_key=True)
    title = Column(Text, nullable=False)


class ReachMap(Base):
    __tablename__ = "reach_map"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    goods_code_prefix = Column(String(6), nullable=False)
    entry_no = Column(Integer, nullable=False)
    limit_value = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True)
    test_method = Column(String(100), nullable=True)
    conditional_rule = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_reach_goods_prefix', 'goods_code_prefix'),
        Index('idx_reach_entry', 'entry_no'),
    )


# Text Index Schema for RAG
class NomenclatureChunks(Base):
    __tablename__ = "nomenclature_chunks"
    __table_args__ = {'schema': 'text_index'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    goods_code = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(String, nullable=False)  # pgvector vector type
    
    __table_args__ = (
        Index('idx_chunks_goods_code', 'goods_code'),
    )


class EvidenceChunks(Base):
    __tablename__ = "evidence_chunks"
    __table_args__ = {'schema': 'text_index'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hs_prefix = Column(String(6), nullable=False)
    chapter = Column(String(2), nullable=False)
    legal_base_id = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(String, nullable=False)  # pgvector vector type
    
    __table_args__ = (
        Index('idx_evidence_hs_prefix', 'hs_prefix'),
        Index('idx_evidence_chapter', 'chapter'),
        Index('idx_evidence_legal_base', 'legal_base_id'),
    )
