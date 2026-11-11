-- O2C Revenue Intelligence
-- MySQL 8.0.16+ (CHECK constraints and functional defaults required)
-- Schema only. No sample rows.
--
-- Business documents use immutable human-readable ids:
--   ACC-2026-000001  Account
--   QTE-2026-000001  Quote
--   SO-2026-000001   Sales order
--   SHP-2026-000001  Shipment
--   INV-2026-000001  Invoice
--   PAY-2026-000001  Payment
--   DSP-2026-000001  Dispute
--   EXC-2026-000001  Exception
-- Line items and status events use surrogate keys. Document ids are supplied
-- by the application and are not updated (ON UPDATE RESTRICT).
--
-- Five anomalies this schema is shaped to detect. Equality across documents
-- is intentionally NOT enforced, so a bad value can be stored and found later.
--   PRICE_VARIANCE      order net price vs quoted net price
--   SHIPMENT_QUANTITY   shipped quantity vs ordered quantity (partial ships are valid)
--   BILLING_MISMATCH    invoice qty/price/amount vs shipment and order, including duplicates and omissions
--   CASH_APPLICATION    payment amount vs allocations vs unapplied cash vs invoice amount paid
--   DISPUTE_LEAKAGE     disputed and credited amounts vs the invoice balance
--
-- Aging uses invoice.due_date, invoice.open_amount, and invoice.status.
-- Reconciliation compares header totals, line sums, allocations, and credits.

CREATE DATABASE IF NOT EXISTS o2c_revenue_intelligence
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE o2c_revenue_intelligence;

SET FOREIGN_KEY_CHECKS = 0;

DROP TRIGGER IF EXISTS trg_status_event_block_update;
DROP TRIGGER IF EXISTS trg_status_event_block_delete;

DROP TABLE IF EXISTS exception;
DROP TABLE IF EXISTS status_event;
DROP TABLE IF EXISTS payment_allocation;
DROP TABLE IF EXISTS dispute;
DROP TABLE IF EXISTS invoice_line;
DROP TABLE IF EXISTS invoice;
DROP TABLE IF EXISTS shipment_line;
DROP TABLE IF EXISTS shipment;
DROP TABLE IF EXISTS order_line;
DROP TABLE IF EXISTS sales_order;
DROP TABLE IF EXISTS quote_line;
DROP TABLE IF EXISTS quote;
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS account;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------------
-- Account: sold-to customer. Payment terms feed invoice due dates.
-- ---------------------------------------------------------------------------
CREATE TABLE account (
  account_id         VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin  NOT NULL,
  account_name       VARCHAR(200) NOT NULL,
  payment_terms_days INT          NOT NULL DEFAULT 30,
  credit_limit       DECIMAL(14,2) NOT NULL,
  currency_code      CHAR(3)      NOT NULL DEFAULT 'USD',
  status             VARCHAR(20)  NOT NULL,
  created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (account_id),
  CONSTRAINT chk_account_id CHECK (
    account_id = UPPER(account_id)
    AND account_id REGEXP '^ACC-[0-9]{4}-[0-9]{6}$'
  ),
  CONSTRAINT chk_account_terms CHECK (payment_terms_days >= 0),
  CONSTRAINT chk_account_credit CHECK (credit_limit >= 0),
  CONSTRAINT chk_account_currency CHECK (
    currency_code = UPPER(currency_code)
    AND currency_code REGEXP '^[A-Z]{3}$'
  ),
  CONSTRAINT chk_account_status CHECK (
    status = UPPER(status)
    AND status IN ('ACTIVE', 'INACTIVE', 'CREDIT_HOLD')
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Quote: commercial offer. One account, many lines, many orders.
-- ---------------------------------------------------------------------------
CREATE TABLE quote (
  quote_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  account_id      VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  quote_date      DATE          NOT NULL,
  valid_until     DATE          NOT NULL,
  status          VARCHAR(20)   NOT NULL,
  currency_code   CHAR(3)       NOT NULL DEFAULT 'USD',
  subtotal        DECIMAL(14,2) NOT NULL,
  discount_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  tax_amount      DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  total_amount    DECIMAL(14,2) NOT NULL,
  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (quote_id),
  KEY idx_quote_account (account_id, status),
  KEY idx_quote_valid (valid_until, status),
  CONSTRAINT fk_quote_account FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_quote_id CHECK (
    quote_id = UPPER(quote_id)
    AND quote_id REGEXP '^QTE-[0-9]{4}-[0-9]{6}$'
  ),
  CONSTRAINT chk_quote_dates CHECK (valid_until >= quote_date),
  CONSTRAINT chk_quote_currency CHECK (
    currency_code = UPPER(currency_code)
    AND currency_code REGEXP '^[A-Z]{3}$'
  ),
  CONSTRAINT chk_quote_amounts CHECK (
    subtotal >= 0
    AND discount_amount >= 0
    AND tax_amount >= 0
    AND total_amount >= 0
    AND discount_amount <= subtotal
    AND total_amount = subtotal - discount_amount + tax_amount
  ),
  CONSTRAINT chk_quote_status CHECK (
    status = UPPER(status)
    AND status IN ('DRAFT', 'OPEN', 'APPROVED', 'REJECTED', 'EXPIRED', 'CONVERTED')
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- QuoteLine: priced products on a quote. Source for PRICE_VARIANCE.
-- ---------------------------------------------------------------------------
CREATE TABLE quote_line (
  quote_line_id   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  quote_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  line_number     INT UNSIGNED    NOT NULL,
  product_code    VARCHAR(40)     NOT NULL,
  product_name    VARCHAR(200)    NOT NULL,
  quantity        DECIMAL(12,3)   NOT NULL,
  unit_price      DECIMAL(14,4)   NOT NULL,
  discount_pct    DECIMAL(5,2)    NOT NULL DEFAULT 0.00,
  net_unit_price  DECIMAL(14,4)   NOT NULL,
  line_amount     DECIMAL(14,2)   NOT NULL,
  created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (quote_line_id),
  UNIQUE KEY uq_quote_line (quote_id, line_number),
  CONSTRAINT fk_quote_line_quote FOREIGN KEY (quote_id) REFERENCES quote (quote_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_quote_line_number CHECK (line_number >= 1),
  CONSTRAINT chk_quote_line_qty CHECK (quantity > 0),
  CONSTRAINT chk_quote_line_price CHECK (
    unit_price >= 0
    AND net_unit_price >= 0
    AND line_amount >= 0
    AND discount_pct >= 0
    AND discount_pct <= 100
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- SalesOrder: accepted demand. Many orders may come from one quote.
-- quote_id stays nullable so an order with no quote can be stored and flagged.
-- ---------------------------------------------------------------------------
CREATE TABLE sales_order (
  sales_order_id     VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  account_id         VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  quote_id           VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NULL,
  order_date         DATE          NOT NULL,
  requested_ship_date DATE         NULL,
  status             VARCHAR(20)   NOT NULL,
  currency_code      CHAR(3)       NOT NULL DEFAULT 'USD',
  subtotal           DECIMAL(14,2) NOT NULL,
  discount_amount    DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  tax_amount         DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  total_amount       DECIMAL(14,2) NOT NULL,
  created_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (sales_order_id),
  KEY idx_so_account (account_id, status),
  KEY idx_so_quote (quote_id),
  KEY idx_so_order_date (order_date),
  CONSTRAINT fk_sales_order_account FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_sales_order_quote FOREIGN KEY (quote_id) REFERENCES quote (quote_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_sales_order_id CHECK (
    sales_order_id = UPPER(sales_order_id)
    AND sales_order_id REGEXP '^SO-[0-9]{4}-[0-9]{6}$'
  ),
  CONSTRAINT chk_sales_order_ship_date CHECK (
    requested_ship_date IS NULL OR requested_ship_date >= order_date
  ),
  CONSTRAINT chk_sales_order_currency CHECK (
    currency_code = UPPER(currency_code)
    AND currency_code REGEXP '^[A-Z]{3}$'
  ),
  CONSTRAINT chk_sales_order_amounts CHECK (
    subtotal >= 0
    AND discount_amount >= 0
    AND tax_amount >= 0
    AND total_amount >= 0
    AND discount_amount <= subtotal
    AND total_amount = subtotal - discount_amount + tax_amount
  ),
  CONSTRAINT chk_sales_order_status CHECK (
    status = UPPER(status)
    AND status IN (
      'DRAFT', 'CONFIRMED', 'PARTIALLY_SHIPPED', 'SHIPPED', 'CLOSED', 'CANCELLED'
    )
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- OrderLine: ordered quantity and selling price.
-- quoted_net_unit_price is the snapshot used for PRICE_VARIANCE.
-- A line with no quote line is allowed (unauthorized line).
-- ---------------------------------------------------------------------------
CREATE TABLE order_line (
  order_line_id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sales_order_id         VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  quote_line_id          BIGINT UNSIGNED NULL,
  line_number            INT UNSIGNED    NOT NULL,
  product_code           VARCHAR(40)     NOT NULL,
  product_name           VARCHAR(200)    NOT NULL,
  quantity_ordered       DECIMAL(12,3)   NOT NULL,
  unit_price             DECIMAL(14,4)   NOT NULL,
  discount_pct           DECIMAL(5,2)    NOT NULL DEFAULT 0.00,
  net_unit_price         DECIMAL(14,4)   NOT NULL,
  quoted_net_unit_price  DECIMAL(14,4)   NULL,
  line_amount            DECIMAL(14,2)   NOT NULL,
  created_at             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (order_line_id),
  UNIQUE KEY uq_order_line (sales_order_id, line_number),
  KEY idx_order_line_quote (quote_line_id),
  CONSTRAINT fk_order_line_sales_order FOREIGN KEY (sales_order_id) REFERENCES sales_order (sales_order_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_order_line_quote_line FOREIGN KEY (quote_line_id) REFERENCES quote_line (quote_line_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_order_line_number CHECK (line_number >= 1),
  CONSTRAINT chk_order_line_qty CHECK (quantity_ordered > 0),
  CONSTRAINT chk_order_line_price CHECK (
    unit_price >= 0
    AND net_unit_price >= 0
    AND line_amount >= 0
    AND discount_pct >= 0
    AND discount_pct <= 100
    AND (quoted_net_unit_price IS NULL OR quoted_net_unit_price >= 0)
  ),
  CONSTRAINT chk_order_line_quote_pair CHECK (
    (quote_line_id IS NULL AND quoted_net_unit_price IS NULL)
    OR (quote_line_id IS NOT NULL AND quoted_net_unit_price IS NOT NULL)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Shipment: one order can have many shipments (partial fulfillment).
-- ---------------------------------------------------------------------------
CREATE TABLE shipment (
  shipment_id     VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin  NOT NULL,
  sales_order_id  VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin  NOT NULL,
  ship_date       DATE         NOT NULL,
  status          VARCHAR(20)  NOT NULL,
  carrier         VARCHAR(100) NULL,
  tracking_number VARCHAR(80)  NULL,
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (shipment_id),
  KEY idx_shipment_order (sales_order_id, ship_date),
  CONSTRAINT fk_shipment_sales_order FOREIGN KEY (sales_order_id) REFERENCES sales_order (sales_order_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_shipment_id CHECK (
    shipment_id = UPPER(shipment_id)
    AND shipment_id REGEXP '^SHP-[0-9]{4}-[0-9]{6}$'
  ),
  CONSTRAINT chk_shipment_status CHECK (
    status = UPPER(status)
    AND status IN ('PLANNED', 'SHIPPED', 'DELIVERED', 'CANCELLED')
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- ShipmentLine: quantity fulfilled for one order line on one shipment.
-- The same order line may appear on later shipments. Over-shipment is allowed
-- so SHIPMENT_QUANTITY can be detected. Sum of quantities is not constrained.
-- ---------------------------------------------------------------------------
CREATE TABLE shipment_line (
  shipment_line_id  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  shipment_id       VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  order_line_id     BIGINT UNSIGNED NOT NULL,
  quantity_shipped  DECIMAL(12,3)   NOT NULL,
  created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (shipment_line_id),
  UNIQUE KEY uq_shipment_line (shipment_id, order_line_id),
  KEY idx_shipment_line_order (order_line_id),
  CONSTRAINT fk_shipment_line_shipment FOREIGN KEY (shipment_id) REFERENCES shipment (shipment_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_shipment_line_order_line FOREIGN KEY (order_line_id) REFERENCES order_line (order_line_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_shipment_line_qty CHECK (quantity_shipped > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Invoice: many invoices may bill one order (partial billing).
-- open_amount supports aging. amount_paid and credit_amount are posted figures
-- and are not forced to match allocations or disputes.
-- ---------------------------------------------------------------------------
CREATE TABLE invoice (
  invoice_id         VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  account_id         VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  sales_order_id     VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  invoice_date       DATE          NOT NULL,
  due_date           DATE          NOT NULL,
  payment_terms_days INT           NOT NULL,
  status             VARCHAR(20)   NOT NULL,
  currency_code      CHAR(3)       NOT NULL DEFAULT 'USD',
  subtotal           DECIMAL(14,2) NOT NULL,
  discount_amount    DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  tax_amount         DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  total_amount       DECIMAL(14,2) NOT NULL,
  amount_paid        DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  credit_amount      DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  open_amount        DECIMAL(14,2) AS (total_amount - amount_paid - credit_amount) STORED,
  created_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (invoice_id),
  KEY idx_invoice_account (account_id, status),
  KEY idx_invoice_order (sales_order_id),
  KEY idx_invoice_aging (status, due_date, open_amount),
  CONSTRAINT fk_invoice_account FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_invoice_sales_order FOREIGN KEY (sales_order_id) REFERENCES sales_order (sales_order_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_invoice_id CHECK (
    invoice_id = UPPER(invoice_id)
    AND invoice_id REGEXP '^INV-[0-9]{4}-[0-9]{6}$'
  ),
  CONSTRAINT chk_invoice_dates CHECK (due_date >= invoice_date),
  CONSTRAINT chk_invoice_terms CHECK (payment_terms_days >= 0),
  CONSTRAINT chk_invoice_currency CHECK (
    currency_code = UPPER(currency_code)
    AND currency_code REGEXP '^[A-Z]{3}$'
  ),
  CONSTRAINT chk_invoice_amounts CHECK (
    subtotal >= 0
    AND discount_amount >= 0
    AND tax_amount >= 0
    AND total_amount >= 0
    AND amount_paid >= 0
    AND credit_amount >= 0
    AND discount_amount <= subtotal
    AND total_amount = subtotal - discount_amount + tax_amount
  ),
  CONSTRAINT chk_invoice_status CHECK (
    status = UPPER(status)
    AND status IN ('DRAFT', 'ISSUED', 'PARTIALLY_PAID', 'PAID', 'DISPUTED', 'VOID')
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- InvoiceLine: billed quantity and price for an order line.
-- shipment_line_id is nullable so a bill-without-shipment can be stored.
-- The same shipment line may be billed on more than one invoice (duplicate bill).
-- line_amount is not forced to equal quantity * unit_price.
-- ---------------------------------------------------------------------------
CREATE TABLE invoice_line (
  invoice_line_id   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  invoice_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  order_line_id     BIGINT UNSIGNED NOT NULL,
  shipment_line_id  BIGINT UNSIGNED NULL,
  line_number       INT UNSIGNED    NOT NULL,
  product_code      VARCHAR(40)     NOT NULL,
  product_name      VARCHAR(200)    NOT NULL,
  quantity          DECIMAL(12,3)   NOT NULL,
  unit_price        DECIMAL(14,4)   NOT NULL,
  line_amount       DECIMAL(14,2)   NOT NULL,
  created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (invoice_line_id),
  UNIQUE KEY uq_invoice_line (invoice_id, line_number),
  KEY idx_invoice_line_order (order_line_id),
  KEY idx_invoice_line_shipment (shipment_line_id),
  CONSTRAINT fk_invoice_line_invoice FOREIGN KEY (invoice_id) REFERENCES invoice (invoice_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_invoice_line_order_line FOREIGN KEY (order_line_id) REFERENCES order_line (order_line_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_invoice_line_shipment_line FOREIGN KEY (shipment_line_id) REFERENCES shipment_line (shipment_line_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_invoice_line_number CHECK (line_number >= 1),
  CONSTRAINT chk_invoice_line_qty CHECK (quantity > 0),
  CONSTRAINT chk_invoice_line_price CHECK (
    unit_price >= 0
    AND line_amount >= 0
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Payment: cash received from an account. One payment can settle many invoices.
-- unapplied_amount is the posted remainder. It is not forced to equal
-- amount minus the sum of allocations (CASH_APPLICATION).
-- ---------------------------------------------------------------------------
CREATE TABLE payment (
  payment_id       VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  account_id       VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  payment_date     DATE          NOT NULL,
  amount           DECIMAL(14,2) NOT NULL,
  unapplied_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  method           VARCHAR(20)   NOT NULL,
  reference_number VARCHAR(80)   NULL,
  status           VARCHAR(20)   NOT NULL,
  currency_code    CHAR(3)       NOT NULL DEFAULT 'USD',
  created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (payment_id),
  KEY idx_payment_account (account_id, payment_date, status),
  KEY idx_payment_reference (reference_number),
  CONSTRAINT fk_payment_account FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_payment_id CHECK (
    payment_id = UPPER(payment_id)
    AND payment_id REGEXP '^PAY-[0-9]{4}-[0-9]{6}$'
  ),
  CONSTRAINT chk_payment_amounts CHECK (
    amount > 0
    AND unapplied_amount >= 0
    AND unapplied_amount <= amount
  ),
  CONSTRAINT chk_payment_method CHECK (
    method = UPPER(method)
    AND method IN ('ACH', 'WIRE', 'CHECK', 'CARD')
  ),
  CONSTRAINT chk_payment_currency CHECK (
    currency_code = UPPER(currency_code)
    AND currency_code REGEXP '^[A-Z]{3}$'
  ),
  CONSTRAINT chk_payment_status CHECK (
    status = UPPER(status)
    AND status IN ('RECEIVED', 'PARTIALLY_APPLIED', 'APPLIED', 'VOID')
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- PaymentAllocation: many-to-many between payments and invoices.
-- One row per payment-invoice pair. allocated_amount may exceed the invoice
-- or the payment; those breaks are cash-application findings, not bad keys.
-- ---------------------------------------------------------------------------
CREATE TABLE payment_allocation (
  allocation_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  payment_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  invoice_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  allocated_amount  DECIMAL(14,2)   NOT NULL,
  created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (allocation_id),
  UNIQUE KEY uq_payment_invoice (payment_id, invoice_id),
  KEY idx_alloc_invoice (invoice_id),
  CONSTRAINT fk_allocation_payment FOREIGN KEY (payment_id) REFERENCES payment (payment_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_allocation_invoice FOREIGN KEY (invoice_id) REFERENCES invoice (invoice_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_allocation_amount CHECK (allocated_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Dispute: many disputes may be open against one invoice.
-- approved_credit_amount is not capped at disputed_amount so leakage
-- (credit above the claim, or claim above the invoice) can be stored.
-- ---------------------------------------------------------------------------
CREATE TABLE dispute (
  dispute_id             VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  invoice_id             VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  account_id             VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin   NOT NULL,
  opened_date            DATE          NOT NULL,
  resolved_date          DATE          NULL,
  reason_code            VARCHAR(30)   NOT NULL,
  disputed_amount        DECIMAL(14,2) NOT NULL,
  approved_credit_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  status                 VARCHAR(20)   NOT NULL,
  resolution_note        VARCHAR(500)  NULL,
  created_at             DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at             DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (dispute_id),
  KEY idx_dispute_invoice (invoice_id, status),
  KEY idx_dispute_account (account_id, status),
  CONSTRAINT fk_dispute_invoice FOREIGN KEY (invoice_id) REFERENCES invoice (invoice_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_dispute_account FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_dispute_id CHECK (
    dispute_id = UPPER(dispute_id)
    AND dispute_id REGEXP '^DSP-[0-9]{4}-[0-9]{6}$'
  ),
  CONSTRAINT chk_dispute_dates CHECK (
    resolved_date IS NULL OR resolved_date >= opened_date
  ),
  CONSTRAINT chk_dispute_reason CHECK (
    reason_code = UPPER(reason_code)
    AND reason_code IN (
      'PRICE', 'QUANTITY', 'DUPLICATE_BILLING', 'TAX', 'QUALITY', 'SHORT_PAY', 'OTHER'
    )
  ),
  CONSTRAINT chk_dispute_amounts CHECK (
    disputed_amount > 0
    AND approved_credit_amount >= 0
  ),
  CONSTRAINT chk_dispute_status CHECK (
    status = UPPER(status)
    AND status IN ('OPEN', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'CLOSED')
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- StatusEvent: append-only history. A new status inserts a row.
-- Previous rows are not updated or deleted (see triggers below).
-- entity_id is the business id of the parent document.
-- ---------------------------------------------------------------------------
CREATE TABLE status_event (
  status_event_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  entity_type     VARCHAR(20)     NOT NULL,
  entity_id       VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  from_status     VARCHAR(20)     NULL,
  to_status       VARCHAR(20)     NOT NULL,
  event_at        DATETIME        NOT NULL,
  actor           VARCHAR(80)     NULL,
  note            VARCHAR(500)    NULL,
  created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (status_event_id),
  KEY idx_status_event_entity (entity_type, entity_id, event_at),
  CONSTRAINT chk_status_event_type CHECK (
    entity_type = UPPER(entity_type)
    AND entity_type IN (
      'ACCOUNT', 'QUOTE', 'SALES_ORDER', 'SHIPMENT',
      'INVOICE', 'PAYMENT', 'DISPUTE', 'EXCEPTION'
    )
  ),
  CONSTRAINT chk_status_event_entity_id CHECK (
    entity_id = UPPER(entity_id)
    AND (
    (entity_type = 'ACCOUNT'     AND entity_id REGEXP '^ACC-[0-9]{4}-[0-9]{6}$')
    OR (entity_type = 'QUOTE'    AND entity_id REGEXP '^QTE-[0-9]{4}-[0-9]{6}$')
    OR (entity_type = 'SALES_ORDER' AND entity_id REGEXP '^SO-[0-9]{4}-[0-9]{6}$')
    OR (entity_type = 'SHIPMENT' AND entity_id REGEXP '^SHP-[0-9]{4}-[0-9]{6}$')
    OR (entity_type = 'INVOICE'  AND entity_id REGEXP '^INV-[0-9]{4}-[0-9]{6}$')
    OR (entity_type = 'PAYMENT'  AND entity_id REGEXP '^PAY-[0-9]{4}-[0-9]{6}$')
    OR (entity_type = 'DISPUTE'  AND entity_id REGEXP '^DSP-[0-9]{4}-[0-9]{6}$')
    OR (entity_type = 'EXCEPTION' AND entity_id REGEXP '^EXC-[0-9]{4}-[0-9]{6}$')
    )
  ),
  CONSTRAINT chk_status_event_from CHECK (
    from_status IS NULL
    OR (
      from_status = UPPER(from_status)
      AND (
        (entity_type = 'ACCOUNT' AND from_status IN ('ACTIVE', 'INACTIVE', 'CREDIT_HOLD'))
        OR (entity_type = 'QUOTE' AND from_status IN ('DRAFT', 'OPEN', 'APPROVED', 'REJECTED', 'EXPIRED', 'CONVERTED'))
        OR (entity_type = 'SALES_ORDER' AND from_status IN ('DRAFT', 'CONFIRMED', 'PARTIALLY_SHIPPED', 'SHIPPED', 'CLOSED', 'CANCELLED'))
        OR (entity_type = 'SHIPMENT' AND from_status IN ('PLANNED', 'SHIPPED', 'DELIVERED', 'CANCELLED'))
        OR (entity_type = 'INVOICE' AND from_status IN ('DRAFT', 'ISSUED', 'PARTIALLY_PAID', 'PAID', 'DISPUTED', 'VOID'))
        OR (entity_type = 'PAYMENT' AND from_status IN ('RECEIVED', 'PARTIALLY_APPLIED', 'APPLIED', 'VOID'))
        OR (entity_type = 'DISPUTE' AND from_status IN ('OPEN', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'CLOSED'))
        OR (entity_type = 'EXCEPTION' AND from_status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'FALSE_POSITIVE'))
      )
    )
  ),
  CONSTRAINT chk_status_event_to CHECK (
    to_status = UPPER(to_status)
    AND (
      (entity_type = 'ACCOUNT' AND to_status IN ('ACTIVE', 'INACTIVE', 'CREDIT_HOLD'))
      OR (entity_type = 'QUOTE' AND to_status IN ('DRAFT', 'OPEN', 'APPROVED', 'REJECTED', 'EXPIRED', 'CONVERTED'))
      OR (entity_type = 'SALES_ORDER' AND to_status IN ('DRAFT', 'CONFIRMED', 'PARTIALLY_SHIPPED', 'SHIPPED', 'CLOSED', 'CANCELLED'))
      OR (entity_type = 'SHIPMENT' AND to_status IN ('PLANNED', 'SHIPPED', 'DELIVERED', 'CANCELLED'))
      OR (entity_type = 'INVOICE' AND to_status IN ('DRAFT', 'ISSUED', 'PARTIALLY_PAID', 'PAID', 'DISPUTED', 'VOID'))
      OR (entity_type = 'PAYMENT' AND to_status IN ('RECEIVED', 'PARTIALLY_APPLIED', 'APPLIED', 'VOID'))
      OR (entity_type = 'DISPUTE' AND to_status IN ('OPEN', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'CLOSED'))
      OR (entity_type = 'EXCEPTION' AND to_status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'FALSE_POSITIVE'))
    )
  ),
  CONSTRAINT chk_status_event_change CHECK (
    from_status IS NULL OR from_status <> to_status
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TRIGGER trg_status_event_block_update
BEFORE UPDATE ON status_event
FOR EACH ROW
SIGNAL SQLSTATE '45000'
  SET MESSAGE_TEXT = 'status_event rows are append-only and cannot be updated';

CREATE TRIGGER trg_status_event_block_delete
BEFORE DELETE ON status_event
FOR EACH ROW
SIGNAL SQLSTATE '45000'
  SET MESSAGE_TEXT = 'status_event rows are append-only and cannot be deleted';

-- ---------------------------------------------------------------------------
-- Exception: one detected anomaly. Several nullable links point at the
-- documents involved. Expected vs actual holds the break that was found.
-- ---------------------------------------------------------------------------
CREATE TABLE exception (
  exception_id      VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  anomaly_code      VARCHAR(30)     NOT NULL,
  severity          VARCHAR(10)     NOT NULL,
  status            VARCHAR(20)     NOT NULL,
  account_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NOT NULL,
  quote_id          VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NULL,
  sales_order_id    VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NULL,
  shipment_id       VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NULL,
  invoice_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NULL,
  payment_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NULL,
  dispute_id        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin     NULL,
  order_line_id     BIGINT UNSIGNED NULL,
  shipment_line_id  BIGINT UNSIGNED NULL,
  invoice_line_id   BIGINT UNSIGNED NULL,
  expected_amount   DECIMAL(14,2)   NULL,
  actual_amount     DECIMAL(14,2)   NULL,
  variance_amount   DECIMAL(14,2)   NULL,
  expected_quantity DECIMAL(12,3)   NULL,
  actual_quantity   DECIMAL(12,3)   NULL,
  description       VARCHAR(500)    NOT NULL,
  detected_at       DATETIME        NOT NULL,
  resolved_at       DATETIME        NULL,
  created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (exception_id),
  KEY idx_exception_account (account_id, status),
  KEY idx_exception_code (anomaly_code, status, detected_at),
  KEY idx_exception_quote (quote_id),
  KEY idx_exception_order (sales_order_id),
  KEY idx_exception_shipment (shipment_id),
  KEY idx_exception_invoice (invoice_id),
  KEY idx_exception_payment (payment_id),
  KEY idx_exception_dispute (dispute_id),
  KEY idx_exception_order_line (order_line_id),
  KEY idx_exception_shipment_line (shipment_line_id),
  KEY idx_exception_invoice_line (invoice_line_id),
  CONSTRAINT fk_exception_account FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_quote FOREIGN KEY (quote_id) REFERENCES quote (quote_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_sales_order FOREIGN KEY (sales_order_id) REFERENCES sales_order (sales_order_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_shipment FOREIGN KEY (shipment_id) REFERENCES shipment (shipment_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_invoice FOREIGN KEY (invoice_id) REFERENCES invoice (invoice_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_payment FOREIGN KEY (payment_id) REFERENCES payment (payment_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_dispute FOREIGN KEY (dispute_id) REFERENCES dispute (dispute_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_order_line FOREIGN KEY (order_line_id) REFERENCES order_line (order_line_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_shipment_line FOREIGN KEY (shipment_line_id) REFERENCES shipment_line (shipment_line_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_exception_invoice_line FOREIGN KEY (invoice_line_id) REFERENCES invoice_line (invoice_line_id)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT chk_exception_id CHECK (
    exception_id = UPPER(exception_id)
    AND exception_id REGEXP '^EXC-[0-9]{4}-[0-9]{6}$'
  ),
  CONSTRAINT chk_exception_code CHECK (
    anomaly_code = UPPER(anomaly_code)
    AND anomaly_code IN (
      'PRICE_VARIANCE',
      'SHIPMENT_QUANTITY',
      'BILLING_MISMATCH',
      'CASH_APPLICATION',
      'DISPUTE_LEAKAGE'
    )
  ),
  CONSTRAINT chk_exception_severity CHECK (
    severity = UPPER(severity)
    AND severity IN ('LOW', 'MEDIUM', 'HIGH')
  ),
  CONSTRAINT chk_exception_status CHECK (
    status = UPPER(status)
    AND status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'FALSE_POSITIVE')
  ),
  CONSTRAINT chk_exception_variance CHECK (
    variance_amount IS NULL
    OR expected_amount IS NULL
    OR actual_amount IS NULL
    OR variance_amount = actual_amount - expected_amount
  ),
  CONSTRAINT chk_exception_resolved CHECK (
    resolved_at IS NULL OR resolved_at >= detected_at
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
