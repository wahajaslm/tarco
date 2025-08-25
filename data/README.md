# WORKFLOW: Data directory structure for Trade Compliance API raw data and processing.
# Used by: ETL pipeline, data ingestion, development setup
# Directory structure:
# 1. raw/ - Place raw XLSX files and ZIP archives here
# 2. extracted/ - Temporary extracted files from ZIP archives
# 3. staging/ - Intermediate data during ETL processing
# 4. processed/ - Final processed data ready for database loading
# 5. backups/ - Database backups and data snapshots
#
# Data flow: raw/ -> extracted/ -> staging/ -> processed/ -> Database -> Vector Index
# This ensures organized data management and reproducible ETL processes.

# Data Directory Structure

## Directory Layout

```
data/
├── raw/                    # Place your raw XLSX files and ZIP archives here
│   ├── taric_export.zip    # Example: TARIC export files
│   ├── vat_rates.xlsx      # Example: VAT rate data
│   ├── geographies.xlsx    # Example: Country/region data
│   └── legal_bases.xlsx    # Example: Legal regulation data
├── extracted/              # Temporary extracted files (auto-generated)
├── staging/                # Intermediate data during ETL (auto-generated)
├── processed/              # Final processed data (auto-generated)
└── backups/                # Database backups (auto-generated)
```

## How to Use

1. **Place Raw Data**: Copy your XLSX files and ZIP archives to `data/raw/`
2. **Run Bootstrap**: Execute the bootstrap script to process all data
3. **Check Results**: Verify data was loaded into database and vector index

## Supported File Formats

- **ZIP archives**: Contain multiple XLSX files (e.g., TARIC exports)
- **XLSX files**: Individual data files (e.g., VAT rates, geographies)
- **CSV files**: Alternative format for simple data

## File Naming Conventions

Use descriptive names for your files:
- `taric_export_YYYYMMDD.zip` - TARIC data exports
- `vat_rates_YYYYMMDD.xlsx` - VAT rate data
- `geographies_YYYYMMDD.xlsx` - Country/region data
- `legal_bases_YYYYMMDD.xlsx` - Legal regulation data

## Data Processing Workflow

1. **Extract**: ZIP files are extracted to `data/extracted/`
2. **Parse**: XLSX files are parsed into structured data
3. **Validate**: Data is validated for consistency and quality
4. **Transform**: Data is transformed to canonical schema
5. **Load**: Data is loaded into PostgreSQL database
6. **Index**: Vector embeddings are created and stored in Qdrant

## Troubleshooting

- Check `logs/etl.log` for processing errors
- Verify file formats and naming conventions
- Ensure sufficient disk space for processing
- Check database connectivity before running bootstrap
