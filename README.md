# CSU EnergyStar Automation

Python automation project for validating and preparing utility data for ENERGY STAR Portfolio Manager upload workflows.

## Project Overview

This project automates utility data preparation and validation for campus energy tracking. The goal is to reduce manual data entry, improve data quality, and prepare upload-ready utility records for ENERGY STAR Portfolio Manager.

The workflow focuses on cleaning, validating, and standardizing utility usage records across campus buildings and meters.

## Key Features

- Cleans utility usage and cost data before upload
- Validates billing start and end dates
- Checks meter active dates against bill periods
- Identifies missing billing gaps
- Detects duplicate or inconsistent records
- Standardizes meter names, building codes, dates, usage, and cost values
- Prepares upload-ready rows for ENERGY STAR Portfolio Manager
- Supports utility types such as steam, chilled water, electric, natural gas, and water

## Data Engineering Workflow

1. Extract utility usage, cost, meter, and billing-period data from source files.
2. Clean and standardize fields such as meter names, building codes, start dates, end dates, usage, and cost.
3. Validate data for missing billing periods, meter date gaps, duplicate records, and unit mismatches.
4. Generate upload-ready rows for ENERGY STAR Portfolio Manager.
5. Support consistent energy tracking and reporting across campus buildings.

## ENERGY STAR Portfolio Manager Integration

This project is designed around the ENERGY STAR Portfolio Manager data upload workflow. It prepares validated utility consumption records in a format that can be reviewed and used for ENERGY STAR meter updates.

The repository does not include private login credentials, internal account details, or direct production access. Any API connection, upload connection, or credential-based workflow should be configured locally and securely outside of this repository.

## Data Engineering Concepts Used

- ETL pipeline design
- Data extraction and transformation
- Data cleaning and standardization
- Data validation and quality checks
- Meter-to-building mapping
- Batch data processing
- CSV/Excel-based ingestion
- Upload-ready data generation
- Error logging and audit tracking

## Tools Used

- Python
- pandas
- openpyxl
- requests
- python-dotenv
- lxml
- Excel
- ENERGY STAR Portfolio Manager

## Folder Structure

```text
csu-energystar-automation/
├── src/
├── sample_data/
├── README.md
├── requirements.txt
└── .gitignore# CSU EnergyStar Automation

This project automates utility data preparation and validation workflows for EnergyStar Portfolio Manager upload processes.

## Project Overview

The goal of this project is to reduce manual data entry and improve data accuracy when preparing utility usage records for EnergyStar Portfolio Manager.

The workflow focuses on cleaning, validating, and preparing upload-ready utility data for campus buildings and meters.

## Key Features

- Cleans utility usage and cost data before upload
- Validates billing start and end dates
- Checks meter active dates against bill periods
- Identifies missing billing gaps
- Detects duplicate or inconsistent records
- Prepares upload-ready rows for EnergyStar Portfolio Manager
- Supports multiple utility types such as steam, chilled water, electric, natural gas, and water

## Tools Used

- Python
- pandas
- openpyxl
- Excel
- EnergyStar Portfolio Manager

## Folder Structure

```text
csu-energystar-automation/
├── src/
├── sample_data/
├── docs/
├── README.md
├── requirements.txt
└── .gitignore


## Data Engineering Workflow

This project follows a data engineering workflow for campus utility data:

1. Extract utility usage, cost, meter, and billing-period data from source files.
2. Clean and standardize fields such as meter names, building codes, start dates, end dates, usage, and cost.
3. Validate the data for missing billing periods, meter date gaps, duplicate records, and unit mismatches.
4. Prepare upload-ready rows for ENERGY STAR Portfolio Manager.
5. Support consistent energy tracking and reporting across campus buildings.

## ENERGY STAR Portfolio Manager Integration

This project is designed around the ENERGY STAR Portfolio Manager data upload workflow. It prepares validated utility consumption records in a format that can be uploaded or used for ENERGY STAR meter updates.

The automation does not include private login credentials, internal account details, or direct production access. Any API or upload connection should be configured locally and securely outside of this repository.

## Data Engineering Concepts Used

- ETL pipeline design
- Data cleaning and transformation
- Data validation
- Meter-to-building mapping
- Batch data processing
- CSV/Excel-based ingestion
- Upload-ready data generation
- Error logging and quality checks

## Repository Privacy

This repository contains code and anonymized sample data only. Real utility bills, CSU internal records, account numbers, building costs, login credentials, and production files are excluded using `.gitignore`.
