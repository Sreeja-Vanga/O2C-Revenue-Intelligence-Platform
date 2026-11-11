# O2C Revenue Intelligence Platform

An end-to-end Order-to-Cash (O2C) analytics platform designed to monitor business transactions, identify revenue leakage, detect operational anomalies, and provide actionable insights across the revenue lifecycle.

## Overview

The Order-to-Cash process involves multiple stages, from customer quotations and sales orders to shipment, invoicing, payment collection, and dispute resolution.

Errors or inconsistencies at any stage can result in revenue leakage, delayed payments, billing discrepancies, and operational inefficiencies.

The **O2C Revenue Intelligence Platform** provides centralized visibility into this lifecycle by analyzing transaction data, detecting anomalies, tracking exceptions, and presenting business insights through an interactive dashboard.

## Key Features

- **Executive Dashboard:** Monitor key business metrics and revenue performance.
- **Transaction Management:** View and analyze quotes, sales orders, shipments, invoices, payments, and disputes.
- **Revenue Leakage Detection:** Identify discrepancies across the order-to-cash lifecycle.
- **Automated Detection Engine:** Detect business rule violations and transaction anomalies.
- **Exception Management:** Track identified exceptions and their financial impact.
- **Lifecycle Tracking:** Monitor transaction status changes and identify irregular transitions.
- **Analytics & Reporting:** Visualize operational trends and generate business insights.
- **Data Generation:** Generate interconnected synthetic business records for analysis and testing.

## O2C Lifecycle

The platform covers the following stages:

1. Quote Creation
2. Sales Order Processing
3. Shipment and Fulfillment
4. Invoice Generation
5. Payment Collection
6. Payment Allocation
7. Dispute Management
8. Exception Detection and Resolution

## Anomaly Detection Scenarios

The platform includes seven injected anomaly scenarios for validating its detection capabilities.

| Anomaly | Description |
|---|---|
| Price Variance | Difference between expected and actual order-line pricing |
| Shipment Quantity | Shipped quantity exceeds the ordered quantity |
| Billing Mismatch | Invoiced quantity does not match shipped quantity |
| Cash Application | Payment allocation exceeds the available payment amount |
| Dispute Leakage | Approved dispute credit is not reflected in the invoice |
| Order Closed Unpaid | Sales order is closed despite an outstanding invoice balance |
| Status Transition Skip | An invalid or skipped transaction status transition |

## Technology Stack

**Frontend**
- React.js
- Vite
- JavaScript
- CSS
- Recharts
- Lucide Icons

**Backend**
- Python
- Flask
- REST APIs

**Database**
- MySQL

**Development & Testing**
- Git and GitHub
- VS Code / Cursor
- Pytest
- MySQL Workbench

## Project Architecture

```text
O2C-Revenue-Intelligence-Platform/
│
├── backend/
│   ├── routes/
│   ├── services/
│   ├── repositories/
│   ├── tests/
│   ├── app.py
│   ├── config.py
│   └── database.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.js
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── data_generator/
│   ├── generator.py
│   ├── anomaly_injector.py
│   ├── ground_truth.py
│   └── config.py
│
├── data/
│   └── ground_truth/
│
├── docs/
├── .gitignore
└── README.md
```

## Database Design

The MySQL database contains interconnected entities representing the O2C lifecycle.

Major tables include:

- Account
- Quote and Quote Line
- Sales Order and Order Line
- Shipment and Shipment Line
- Invoice and Invoice Line
- Payment and Payment Allocation
- Dispute
- Status Event
- Exception

Primary keys, foreign keys, and relational constraints maintain consistency between dependent transaction records.

## Installation and Setup

### Prerequisites

- Python 3.12 or compatible version
- Node.js and npm
- MySQL Server
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Sreeja-Vanga/O2C-Revenue-Intelligence-Platform.git
cd O2C-Revenue-Intelligence-Platform
```

### 2. Configure the database

1. Start MySQL Server.
2. Create the database named `o2c_revenue_intelligence`.
3. Execute `database/schema.sql` to create the tables.
4. Configure database credentials using the project's environment configuration.

**Important:** Use the existing generated dataset if you have received the populated database. Do not rerun the schema or data generators against an existing populated database without understanding their effects.

### 3. Set up the backend

```bash
python -m venv venv
```

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Configure the required environment variables using the project's configuration files and `.env.example`, if provided.

Start the backend:

```bash
python -m backend.app
```

### 4. Set up the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite in your browser.

## Testing

Run the backend test suite from the project root:

```bash
python -m pytest backend/tests -v
```

The test suite covers API functionality, database utilities, dashboard and analytics endpoints, and anomaly detection behavior.

## Project Highlights

- Designed a relational data model representing the complete O2C lifecycle.
- Generated interconnected synthetic business transaction records.
- Introduced controlled anomaly scenarios for testing detection logic.
- Developed a Flask backend with modular routes, services, and repositories.
- Built a React-based interface for business analytics and transaction visibility.
- Implemented automated tests for backend functionality and anomaly detection.

## Future Enhancements

- Role-based access control for different business users.
- Advanced predictive analytics for payment delays.
- Machine learning-based revenue leakage prediction.
- Automated exception prioritization.
- Enhanced reporting and export capabilities.

## Author

**Sreeja Vanga**

B.Tech – Information Technology

GitHub: https://github.com/Sreeja-Vanga
