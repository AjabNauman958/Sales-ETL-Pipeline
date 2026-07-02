import logging
import os
from datetime import datetime
import time
import pandas as pd
from sqlalchemy import create_engine, text

# CONFIGURATION

JSON_FILE = "data/sales_data.json"
INVALID_DATA_FILE = "data/invalid_records.csv"
LOG_FILE = "logs/etl.log"

LOG_FILE = (f"logs/etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

HOST = "localhost"
PORT = "5432"
DATABASE = "sales_assessment"
USER = "postgres"
PASSWORD = "admin1234"

engine = create_engine(
    f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
)

# print(engine.url)


def setup_logging():

    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        filemode="a"
    )


def get_last_loaded_date():

    query = """
        SELECT last_loaded_date
        FROM public.etl_metadata
        WHERE pipeline_name = 'SalesPipeline'
    """

    with engine.connect() as conn:
        result = conn.execute(text(query)).fetchone()

    if result:
        logging.info(f"Last Loaded Date : {result[0]}")
        return result[0]

    logging.info("No previous load found. Initial load.")

    # logging.info(datetime(1900, 1, 1))

    return datetime(1900, 1, 1)


def extract_data():

    logging.info("Reading JSON file...")

    df = pd.read_json(JSON_FILE)

    logging.info(f"Records Read : {len(df)}")

    product_df = pd.json_normalize(df["product"])

    product_df.columns = [
        "product_id",
        "product_name",
        "category",
        "price"
    ]

    df = df.drop(columns=["product"])

    df = pd.concat(
        [
            df.reset_index(drop=True),
            product_df.reset_index(drop=True)
        ],
        axis=1
    )

    # logging.info(df)

    # df["transaction_date"] = pd.to_datetime(
    #     df["date"],
    #     errors="coerce"
    # )

    df["transaction_date"] = pd.to_datetime(
        df["date"],
        format="mixed",
        errors="coerce",
        utc=True
    ).dt.tz_localize(None)

    df.drop(columns=["date"], inplace=True)

    # logging.info(df)

    # Incremental Load

    last_loaded_date = get_last_loaded_date()

    df = df[
        df["transaction_date"] > last_loaded_date
    ].copy()

    # logging.info(df)

    logging.info(
        f"Incremental Records : {len(df)}"
    )

    return df


def validate_data(df):

    logging.info("Validating data...")

    valid_records = []
    invalid_records = []

    duplicate_ids = set(
        df[df.duplicated("transaction_id")]["transaction_id"]
    )

    for _, row in df.iterrows():

        errors = []

        load_record = True

        if pd.isna(row["customer_id"]):
            errors.append("Missing CustomerID")

        if pd.isna(row["transaction_date"]):
            errors.append("Invalid Date")
            load_record = False

        if row["quantity"] <= 0:
            errors.append("Invalid Quantity")
            load_record = False

        if row["price"] <= 0:
            errors.append("Invalid Price")
            load_record = False

        if row["transaction_id"] in duplicate_ids:
            errors.append("Duplicate TransactionID")
            load_record = False

        if errors:
            invalid_row = row.copy()
            invalid_row["validation_error"] = ", ".join(errors)
            invalid_row["logged_at"] = datetime.now()
            invalid_records.append(invalid_row)

        if load_record:
            valid_row = row.copy()
            valid_row["loaded_at"] = datetime.now()
            valid_records.append(valid_row)

    valid_df = pd.DataFrame(valid_records)

    invalid_df = pd.DataFrame(invalid_records)

    # logging.info(f"Valid Records   : {valid_df}")   
    # logging.info(f"Invalid Records : {invalid_df}")

    logging.info(f"Valid Records   : {len(valid_df)}")
    logging.info(f"Invalid Records : {len(invalid_df)}")

    return valid_df, invalid_df


def save_invalid_data(df):

    if df.empty:
        return

    os.makedirs("data", exist_ok=True)

    df.to_csv(
        INVALID_DATA_FILE,
        index=False
    )

    logging.info(
        f"Invalid data saved : {INVALID_DATA_FILE}"
    )


def clean_data(df):

    logging.info("Cleaning data...")

    df = df.copy()

    df["discount"] = df["discount"].fillna(0)

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    return df


def transform_data(df):

    logging.info("Transforming data...")

    df = df.copy()

    df["gross_amount"] = (
        df["price"] *
        df["quantity"]
    )

    df["net_amount"] = (
        df["gross_amount"] *
        (1 - df["discount"])
    )

    amount_columns = [
        "price",
        "discount",
        "gross_amount",
        "net_amount"
    ]

    df[amount_columns] = df[amount_columns].round(2)

    logging.info(df)

    return df


def load_customers(conn, df):

    logging.info("Loading customers...")

    customers = (
        df[["customer_id", "region", "loaded_at"]]
        .drop_duplicates(subset=["customer_id"])
    )

    # existing_customers = pd.read_sql(
    #     "SELECT * FROM public.Customers",
    #     conn
    # )

    # print(existing_customers)
    # print(existing_customers.columns.tolist())

    existing_customers = pd.read_sql(
        "SELECT customer_id FROM public.customers",
        conn
    )

    customers = customers[
        ~customers["customer_id"].isin(
            existing_customers["customer_id"]
        )
    ]

    if not customers.empty:
        customers.to_sql(
            "customers",
            conn,
            if_exists="append",
            index=False
        )

    logging.info(
        f"Customers Inserted : {len(customers)}"
    )


def load_products(conn, df):

    logging.info("Loading products...")

    products = (
        df[
            [
                "product_id",
                "product_name",
                "category",
                "price",
                "loaded_at"
            ]
        ]
        .drop_duplicates(subset=["product_id"])
    )

    existing_products = pd.read_sql(
        "SELECT product_id FROM public.products",
        conn
    )

    products = products[
        ~products["product_id"].isin(
            existing_products["product_id"]
        )
    ]

    if not products.empty:
        products.to_sql(
            "products",
            conn,
            if_exists="append",
            index=False
        )

    logging.info(
        f"Products Inserted : {len(products)}"
    )


def load_transactions(conn, df):

    logging.info("Loading transactions...")

    transactions = (
        df[
            [
                "transaction_id",
                "customer_id",
                "product_id",
                "quantity",
                "price",
                "discount",
                "gross_amount",
                "net_amount",
                "transaction_date",
                "loaded_at"
            ]
        ].rename(
            columns={
                "price": "unit_price"
            }
        )
    )

    existing_transactions = pd.read_sql(
        "SELECT transaction_id FROM public.transactions",
        conn
    )

    transactions = transactions[
        ~transactions["transaction_id"].isin(
            existing_transactions["transaction_id"]
        )
    ]

    if not transactions.empty:
        transactions.to_sql(
            "transactions",
            conn,
            if_exists="append",
            index=False,
            chunksize=500
        )

    logging.info(
        f"Transactions Inserted : {len(transactions)}"
    )


def update_metadata(conn, df):

    if df.empty:
        return

    last_loaded_date = pd.to_datetime(
        df["transaction_date"]
    ).max()

    query = text("""
        INSERT INTO public.etl_metadata
        (
            pipeline_name,
            last_loaded_date
        )
        VALUES
        (
            'SalesPipeline',
            :last_loaded_date
        )
        ON CONFLICT (pipeline_name)
        DO UPDATE SET
        last_loaded_date = EXCLUDED.last_loaded_date;
        """)

    conn.execute(
        query,
        {
            "last_loaded_date": last_loaded_date
        }
    )

    logging.info(
        f"Metadata Updated : {last_loaded_date}"
    )


def run_pipeline():

    start_time = time.time()

    setup_logging()

    logging.info("Sales ETL Pipeline Started")

    try:

        df = extract_data()

        if df.empty:
            logging.info("No new records found.")
            print("No new records found.")
            return

        valid_df, invalid_df = validate_data(df)

        save_invalid_data(invalid_df)

        if valid_df.empty:
            logging.warning("No valid records available.")
            print("No valid records available.")
            return

        clean_df = clean_data(valid_df)

        transformed_df = transform_data(clean_df)

        with engine.begin() as conn:
            load_customers(conn, transformed_df)
            load_products(conn, transformed_df)
            load_transactions(conn, transformed_df)
            update_metadata(conn, transformed_df)

        execution_time = round( time.time() - start_time, 2)

        logging.info("Pipeline Completed Successfully")
        logging.info(f"Rows Read        : {len(df)}")
        logging.info(f"Rows Loaded      : {len(transformed_df)}")
        logging.info(f"Rows Rejected    : {len(invalid_df)}")
        logging.info(f"Execution Time   : {execution_time} seconds")

        # print("\nPipeline Completed Successfully")
        # print(f"Rows Read      : {len(df)}")
        # print(f"Rows Loaded    : {len(transformed_df)}")
        # print(f"Rows Rejected  : {len(invalid_df)}")
        # print(f"Execution Time : {execution_time} seconds")

    except Exception as ex:

        logging.exception("Pipeline Failed")

        print("\nPipeline Failed")
        print(ex)

        raise

if __name__ == "__main__":
    run_pipeline()