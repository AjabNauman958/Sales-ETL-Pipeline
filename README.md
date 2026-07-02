# Sales ETL Pipeline Assessment

## Overview

This project implements a Python-based ETL pipeline that processes semi-structured sales data from a JSON source and loads it into a normalized PostgreSQL database. The solution includes data validation, cleaning, transformation, incremental loading, logging and analytical SQL queries.

## Project Structure

```text
sales-etl-assessment/
│
├── data/
│   ├── sales_data.json
│   └── invalid_records.csv
│
├── logs/
│   └── etl.log
│
├── sql/
│   ├── create_schema.sql
│   └── analytical_queries.sql
│
├── src/
│   ├── etl_pipeline.py
│
├── requirements.txt
└── README.md
```

## Technologies Used

* Python 3.x
* Pandas
* SQLAlchemy
* psycopg2-binary
* PostgreSQL

## ETL Workflow

The pipeline performs the following steps:

1. Extract sales data from a JSON file.
2. Normalize the nested product object into separate columns.
3. Convert transaction dates into a standard datetime format.
4. Apply incremental loading using the last successful load date stored in the metadata table.
5. Validate incoming records.
6. Clean and transform the data.
7. Load Customers, Products and Transactions into PostgreSQL.
8. Update the ETL metadata table.
9. Generate log and invalid records files.

## Validation Rules

| Rule                             | Action                                                      |
| -------------------------------- | ----------------------------------------------------------- |
| Missing Customer ID              | Transaction is loaded and recorded in `invalid_records.csv` |
| Invalid Transaction Date         | Record rejected                                             |
| Quantity less than or equal to 0 | Record rejected                                             |
| Price less than or equal to 0    | Record rejected                                             |
| Duplicate Transaction ID         | Record skipped                                              |

## Data Transformation

The following transformations are applied:

* Replace null discounts with `0`.
* Standardize transaction date format.
* Calculate Gross Amount (`Price × Quantity`).
* Calculate Net Amount (`Gross Amount × (1 - Discount)`).
* Round all monetary values to two decimal places.

## Incremental Loading

The pipeline supports incremental loading using the `ETL_Metadata` table.

During each execution:

* The last successful load date is retrieved from the metadata table.
* Only transactions newer than the stored date are processed.
* After a successful load, the metadata table is updated with the latest transaction date.

This prevents previously loaded records from being processed again.

## Database Design

The database consists of four tables:

* Customers
* Products
* Transactions
* ETL_Metadata

Primary keys, foreign keys and indexes have been created to maintain data integrity and improve query performance.

I created indexes on columns that are frequently used in filtering, joins and reporting. For example, customer_id and product_id are used in joins, transaction_date is used for incremental loading and date-based reports and region and category are commonly used in analytical queries. These indexes reduce the amount of data PostgreSQL needs to scan, improving query performance, especially as the tables grow.

## Analytical SQL Queries

The following analytical queries are included:

### 1. Total sales by region and category.
   <img width="701" height="501" alt="image" src="https://github.com/user-attachments/assets/002da806-cc8e-4f01-8e36-955b4dfc3d8a" />
   
### 2. Top 5 products by total revenue.
   <img width="847" height="573" alt="image" src="https://github.com/user-attachments/assets/bfe69913-98b2-409c-99d5-03f7e1a9bf3e" />
   
### 3. Monthly sales trend.
   <img width="635" height="440" alt="image" src="https://github.com/user-attachments/assets/7d5affa6-ef30-4afe-bffb-1368a2ac2e71" />
   
### 4. Average discount percentage by region.
   <img width="737" height="435" alt="image" src="https://github.com/user-attachments/assets/8d4203e0-bee2-4b46-9360-9f65d926d264" />
   
### 5. Number of transactions with total sales greater than $1000.
   <img width="396" height="287" alt="image" src="https://github.com/user-attachments/assets/75f5e3ee-68b9-4051-ad23-d7e33792e09e" />


## Logging

The pipeline generates an `etl.log` file containing:

* Pipeline start and completion time
* Number of records processed
* Number of valid and invalid records
* Number of records loaded into each table
* Execution status and errors (if any)

## Invalid Records

Records that fail validation or transactions with missing customer IDs, are written to `invalid_records.csv` along with the corresponding validation reason. This provides traceability while allowing valid business transactions to continue through the pipeline where applicable.

## How to Run

1. Clone the repository.
2. Install the required Python packages.

```bash
pip install -r requirements.txt
```

3. Create the database using `sql/create_schema.sql`.
4. Update the PostgreSQL connection details in `src/etl_pipeline.py`.
5. Place the JSON dataset in the `data` folder.
6. Run the ETL pipeline.

```bash
python src/etl_pipeline.py
```
