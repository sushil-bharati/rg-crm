# RG CRM API

FastAPI-based CRM system that manages customer records, orders, and addresses with analytics capabilities.

## Features

- Customer management with duplicate prevention (unique email and telephone)
- Multiple address support (billing and shipping) per customer
- Order tracking for both in-store and online purchases
- Multiple shipping addresses per order
- Analytics endpoints for business insights
- Comprehensive test suite

## Tech Stack

- Python 3.11
- FastAPI
- SQLite
- SQLAlchemy (psycopg can be utilized for Postgres with the same codebase)
- pytest (testing)

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── database.py      # Database configuration
│   └── crud.py          # CRUD operations
├── tests/
│   └── test_api.py      # Unit tests
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Setup

### Prerequisites

- Python 3.13.5 or above
- Upgraded `pip` for package management

### Getting Started

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <path to rg-crm dir>
   ```

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run all tests (if any import issues, make sure you installed the requirements as described above). 
This step will create `test.db` file inside `tests` directory.
   ```bash
   pytest
   ```

4. [OPTIONAL] To run the API endpoint locally:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Customers

- `POST /customers/` - Create a new customer
- `GET /customers/history/` - Get customer order history by email or telephone

### Orders

- `POST /customers/{customer_id}/orders/` - Create a new order for a customer

### Analytics

- `GET /analytics/orders/by-zip/` - Aggregates order count by billing or shipping ZIP code
- `GET /analytics/in-store/hours/` - Most in-store purchase hours
- `GET /analytics/in-store/top-customers/` - Top-5 customers with the most in-store orders

## API Documentation

If you ran the server (Step# 4 above), you may visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`