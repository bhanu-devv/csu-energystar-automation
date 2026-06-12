# CSU EnergyStar Automation

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
