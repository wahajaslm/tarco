# WORKFLOW: ETL (Extract, Transform, Load) package for data ingestion and processing.
# Used by: Data ingestion, database population, vector indexing
# Modules include:
# 1. ingest_zip.py - Extract data from ZIP files containing XLSX exports
# 2. transform_canonical.py - Transform staging data to canonical schema
# 3. duty_parser.py - Parse duty formats (ad valorem, specific, compound)
# 4. validators.py - Validate data consistency and integrity
# 5. build_vector_index.py - Build vector embeddings for RAG pipeline
#
# ETL flow: XLSX ZIP -> Extract -> Staging -> Transform -> Canonical DB -> Vector Index
# This ensures all trade compliance data is properly ingested and indexed for the API.

"""
ETL package for Trade Compliance API data ingestion and processing.
"""
