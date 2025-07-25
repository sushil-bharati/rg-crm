import pytest
import sys
import os
import random
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.main import app
from app.models import OrderType, AddressType

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_customer(test_db):
    customer_data = {
        "telephone": "1234567890",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "addresses": [
            {
                "type": "billing",
                "street": "123 Main St",
                "city": "Test City",
                "state": "TS",
                "zip_code": "12345"
            }
        ]
    }
    
    response = client.post("/customers/", json=customer_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == customer_data["email"]
    assert data["telephone"] == customer_data["telephone"]
    assert data["first_name"] == customer_data["first_name"]
    assert data["last_name"] == customer_data["last_name"]
    assert len(data["addresses"]) == 1
    assert data["addresses"][0]["type"] == customer_data["addresses"][0]["type"]
    assert data["addresses"][0]["street"] == customer_data["addresses"][0]["street"]
    assert data["addresses"][0]["city"] == customer_data["addresses"][0]["city"]
    assert data["addresses"][0]["state"] == customer_data["addresses"][0]["state"]
    assert data["addresses"][0]["zip_code"] == customer_data["addresses"][0]["zip_code"]


def test_create_duplicate_customer(test_db):
    customer_data = {
        "telephone": "1234567890",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "addresses": [
            {
                "type": "billing",
                "street": "123 Main St",
                "city": "Test City",
                "state": "TS",
                "zip_code": "12345"
            }
        ]
    }
    
    # Create first customer
    response = client.post("/customers/", json=customer_data)
    assert response.status_code == 200

    # Try to create duplicate customer
    response = client.post("/customers/", json=customer_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_create_order(test_db):
    # First create a customer - this time with multiple shipping addresses
    customer_data = {
        "telephone": "1234567890",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "addresses": [
            {
                "type": "billing",
                "street": "123 Main St",
                "city": "Test City",
                "state": "TS",
                "zip_code": "12345"
            },
            {
                "type": "shipping",
                "street": "987 Corp St",
                "city": "XYZ City",
                "state": "MK",
                "zip_code": "98566-9658"
            }
        ]
    }
    
    customer_response = client.post("/customers/", json=customer_data)
    customer_id = customer_response.json()["id"]
    billing_address_id = customer_response.json()["addresses"][0]["id"]
    shipping_address_id = customer_response.json()["addresses"][1]["id"]

    # Create an order
    order_data = {
        "order_type": "in_store",
        "total_amount": 100.50,
        "billing_address_id": billing_address_id,
        "shipping_address_ids": [shipping_address_id]
    }

    response = client.post(f"/customers/{customer_id}/orders/", json=order_data)
    assert response.status_code == 200
    data = response.json()
    assert data["order_type"] == order_data["order_type"]
    assert data["total_amount"] == order_data["total_amount"]
    assert data["billing_address"]["id"] == billing_address_id
    assert len(data["shipping_addresses"]) == 1
    assert data["shipping_addresses"][0]["id"] == shipping_address_id

def test_get_customer_order_history_by_email(test_db):
    # Create a customer with an order
    customer_data = {
        "telephone": "1234567890",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "addresses": [
            {
                "type": "billing",
                "street": "123 Main St",
                "city": "Test City",
                "state": "TS",
                "zip_code": "12345"
            },
            {
                "type": "shipping",
                "street": "987 Corp St",
                "city": "XYZ City",
                "state": "MK",
                "zip_code": "98566-9658"
            }
        ]
    }
    
    customer_response = client.post("/customers/", json=customer_data)
    customer_id = customer_response.json()["id"]
    billing_address_id = customer_response.json()["addresses"][0]["id"]
    shipping_address_id = customer_response.json()["addresses"][1]["id"]

    # Make 3 in-store orders
    for _ in range(3):
        order_data = {
                "order_type": "in_store",
                "total_amount": random.random(),
                "billing_address_id": billing_address_id,
                "shipping_address_ids": [shipping_address_id]
        }
        client.post(f"/customers/{customer_id}/orders/", json=order_data)

    # Get customer history by email
    response = client.get("/customers/history/", params={"identifier": "test@example.com", "is_email": True})
    assert response.status_code == 200
    data = response.json()
    assert len(data["orders"]) == 3
    assert data["customer"]["email"] == customer_data["email"]

        # Check if billing and shipping addresses for ALL orders are correct
    for i in range(3):
        assert data["orders"][i]["billing_address"]["street"] == customer_data["addresses"][0]["street"]
        assert data["orders"][i]["billing_address"]["city"] == customer_data["addresses"][0]["city"]
        assert data["orders"][i]["billing_address"]["state"] == customer_data["addresses"][0]["state"]
        assert data["orders"][i]["billing_address"]["zip_code"] == customer_data["addresses"][0]["zip_code"]
        assert data["orders"][i]["billing_address"]["type"] == customer_data["addresses"][0]["type"]
    
        assert data["orders"][i]["shipping_addresses"][0]["street"] == customer_data["addresses"][1]["street"]
        assert data["orders"][i]["shipping_addresses"][0]["city"] == customer_data["addresses"][1]["city"]
        assert data["orders"][i]["shipping_addresses"][0]["state"] == customer_data["addresses"][1]["state"]
        assert data["orders"][i]["shipping_addresses"][0]["zip_code"] == customer_data["addresses"][1]["zip_code"]
        assert data["orders"][i]["shipping_addresses"][0]["type"] == customer_data["addresses"][1]["type"]

def test_get_customer_order_history_by_phone(test_db):
    # Create a customer with an order
    customer_data = {
        "telephone": "123-456-7890",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "addresses": [
            {
                "type": "billing",
                "street": "123 Main St",
                "city": "Test City",
                "state": "TS",
                "zip_code": "12345"
            },
            {
                "type": "shipping",
                "street": "987 Corp St",
                "city": "XYZ City",
                "state": "MK",
                "zip_code": "98566-9658"
            }
        ]
    }
    
    customer_response = client.post("/customers/", json=customer_data)
    customer_id = customer_response.json()["id"]
    billing_address_id = customer_response.json()["addresses"][0]["id"]
    shipping_address_id = customer_response.json()["addresses"][1]["id"]

    # Make 3 in-store orders
    for _ in range(3):
        order_data = {
                "order_type": "in_store",
                "total_amount": random.random(),
                "billing_address_id": billing_address_id,
                "shipping_address_ids": [shipping_address_id]
        }
        client.post(f"/customers/{customer_id}/orders/", json=order_data)

    # Get customer history by email
    response = client.get("/customers/history/", params={"identifier": "123-456-7890", "is_email": False})
    assert response.status_code == 200
    data = response.json()
    assert len(data["orders"]) == 3
    assert data["customer"]["telephone"] == customer_data["telephone"]
    
    # Check if billing and shipping addresses for ALL orders are correct
    for i in range(3):
        assert data["orders"][i]["billing_address"]["street"] == customer_data["addresses"][0]["street"]
        assert data["orders"][i]["billing_address"]["city"] == customer_data["addresses"][0]["city"]
        assert data["orders"][i]["billing_address"]["state"] == customer_data["addresses"][0]["state"]
        assert data["orders"][i]["billing_address"]["zip_code"] == customer_data["addresses"][0]["zip_code"]
        assert data["orders"][i]["billing_address"]["type"] == customer_data["addresses"][0]["type"]
    
        assert data["orders"][i]["shipping_addresses"][0]["street"] == customer_data["addresses"][1]["street"]
        assert data["orders"][i]["shipping_addresses"][0]["city"] == customer_data["addresses"][1]["city"]
        assert data["orders"][i]["shipping_addresses"][0]["state"] == customer_data["addresses"][1]["state"]
        assert data["orders"][i]["shipping_addresses"][0]["zip_code"] == customer_data["addresses"][1]["zip_code"]
        assert data["orders"][i]["shipping_addresses"][0]["type"] == customer_data["addresses"][1]["type"]
