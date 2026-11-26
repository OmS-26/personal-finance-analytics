-- Personal Finance Analytics: schema (MySQL 8.0+ / MariaDB 10.6+)
-- Amounts are signed: positive = money in (income, transfers in), negative = money out.

DROP DATABASE IF EXISTS finance_analytics;
CREATE DATABASE finance_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE finance_analytics;

CREATE TABLE users (
    user_id     INT AUTO_INCREMENT PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    city        VARCHAR(60)  NOT NULL,
    created_at  DATE         NOT NULL
);

CREATE TABLE accounts (
    account_id       INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL,
    account_type     ENUM('Chequing', 'Savings', 'Credit Card') NOT NULL,
    opening_balance  DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    opened_on        DATE NOT NULL,
    CONSTRAINT fk_accounts_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT uq_user_account_type UNIQUE (user_id, account_type)
);

CREATE TABLE categories (
    category_id    INT AUTO_INCREMENT PRIMARY KEY,
    category_name  VARCHAR(50) NOT NULL UNIQUE,
    category_type  ENUM('Income', 'Expense', 'Transfer') NOT NULL
);

CREATE TABLE merchants (
    merchant_id          INT AUTO_INCREMENT PRIMARY KEY,
    merchant_name        VARCHAR(100) NOT NULL UNIQUE,
    default_category_id  INT NOT NULL,
    CONSTRAINT fk_merchants_category FOREIGN KEY (default_category_id) REFERENCES categories(category_id)
);

CREATE TABLE transactions (
    transaction_id    INT AUTO_INCREMENT PRIMARY KEY,
    account_id        INT NOT NULL,
    merchant_id       INT NOT NULL,
    category_id       INT NOT NULL,
    amount            DECIMAL(10,2) NOT NULL,
    transaction_date  DATE NOT NULL,
    CONSTRAINT fk_txn_account  FOREIGN KEY (account_id)  REFERENCES accounts(account_id),
    CONSTRAINT fk_txn_merchant FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
    CONSTRAINT fk_txn_category FOREIGN KEY (category_id) REFERENCES categories(category_id),
    CONSTRAINT chk_amount_nonzero CHECK (amount <> 0)
);

-- Most queries filter or partition by account + date, or group by category + date.
CREATE INDEX idx_txn_account_date  ON transactions (account_id, transaction_date);
CREATE INDEX idx_txn_category_date ON transactions (category_id, transaction_date);
CREATE INDEX idx_txn_merchant      ON transactions (merchant_id);
