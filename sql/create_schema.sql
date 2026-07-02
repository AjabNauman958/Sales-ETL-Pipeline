-- Customer table
CREATE TABLE customers
(
    customer_id VARCHAR(20) PRIMARY KEY,
    region VARCHAR(50) NOT NULL,
	loaded_at TIMESTAMP NOT NULL
);

-- Product
CREATE TABLE products
(
    product_id VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
	loaded_at TIMESTAMP NOT NULL
);

-- Transactions
CREATE TABLE transactions
(
    transaction_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NULL,
    product_id VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
	unit_price DECIMAL(10,2) NOT NULL,
    discount DECIMAL(5,2) NOT NULL,
	gross_amount DECIMAL(12,2) NOT NULL,
	net_amount DECIMAL(12,2) NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
	loaded_at TIMESTAMP NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);


--- meta data
CREATE TABLE etl_metadata
(
    pipeline_name VARCHAR(100) PRIMARY KEY,
    last_loaded_date TIMESTAMP
);

--- indexes
CREATE INDEX IX_transaction_date
ON transactions(transaction_date);

CREATE INDEX IX_Transactions_Product
ON transactions(product_id);

CREATE INDEX IX_Transactions_Customer
ON transactions(customer_id);

CREATE INDEX IX_Customers_Region
ON customers(region);

CREATE INDEX IX_Products_Category
ON products(category);



select * from public.customers;
select * from public.products;
select * from public.transactions;
select * from public.etl_metadata;

