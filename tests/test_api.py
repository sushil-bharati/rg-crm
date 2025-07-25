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

def test_analytics_orders_by_shipping_zip(test_db):
    # Create test customer first
    customer_data = {
        "telephone": "123-456-7890",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "addresses": [
            {
                "type": "billing",
                "street": "123 Main St",
                "city": "Bill City",
                "state": "BC",
                "zip_code": "12345-6789"
            },
            {
                "type": "shipping",
                "street": "987 Main St",
                "city": "Ship1 City",
                "state": "SC",
                "zip_code": "98765-4321"
            },
            {
                "type": "shipping",
                "street": "999 Main St",
                "city": "Ship2 City",
                "state": "XS",
                "zip_code": "01234-9876"
            }
        ]
    }
    
    customer_response = client.post("/customers/", json=customer_data)
    customer_id = customer_response.json()["id"]
    billing_address_id = customer_response.json()["addresses"][0]["id"]
    shipping_address_id_1 = customer_response.json()["addresses"][1]["id"]
    shipping_address_id_2 = customer_response.json()["addresses"][2]["id"]

    # Create multiple orders across shipping addresses
    # In the first shipping address, create 3 orders
    for _ in range(3):
        order_data = {
            "order_type": "in_store",
            "total_amount": random.random(),
            "billing_address_id": billing_address_id,
            "shipping_address_ids": [shipping_address_id_1]
        }
        client.post(f"/customers/{customer_id}/orders/", json=order_data)
    # In the second shipping address, create 10 orders
    for _ in range(10):
        order_data = {
            "order_type": "in_store",
            "total_amount": random.random(),
            "billing_address_id": billing_address_id,
            "shipping_address_ids": [shipping_address_id_2]
        }
        client.post(f"/customers/{customer_id}/orders/", json=order_data)

    # Test wrt shipping zip code, by default: ascending = True
    response = client.get("/analytics/orders/by-zip/", params={"is_billing": False})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["zip_code"] == "98765-4321"
    assert data[0]["order_count"] == 3
    assert data[1]["zip_code"] == "01234-9876"
    assert data[1]["order_count"] == 10

def test_analytics_orders_by_billing_zip(test_db):
    # Create test customer first
    customer_data = {
        "telephone": "123-456-7890",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "addresses": [
            {
                "type": "billing",
                "street": "123 Main St",
                "city": "Bill City",
                "state": "BC",
                "zip_code": "12345-6789"
            },
            {
                "type": "billing",
                "street": "987 Main St",
                "city": "Bill Pop City",
                "state": "SC",
                "zip_code": "98765-4321"
            },
            {
                "type": "shipping",
                "street": "404 Side St",
                "city": "Ship City",
                "state": "XY",
                "zip_code": "96365"
            }
        ]
    }
    
    customer_response = client.post("/customers/", json=customer_data)
    customer_id = customer_response.json()["id"]
    billing_address_id_1 = customer_response.json()["addresses"][0]["id"]
    billing_address_id_2 = customer_response.json()["addresses"][1]["id"]
    shipping_address_id = customer_response.json()["addresses"][1]["id"]

    # Create multiple orders
    # In the first billing address, create 7 orders
    for _ in range(7):
        order_data = {
            "order_type": "in_store",
            "total_amount": random.random(),
            "billing_address_id": billing_address_id_1,
            "shipping_address_ids": [shipping_address_id]
        }
        client.post(f"/customers/{customer_id}/orders/", json=order_data)
    # In the second billing address, create 15 orders
    for _ in range(15):
        order_data = {
            "order_type": "in_store",
            "total_amount": random.random(),
            "billing_address_id": billing_address_id_2,
            "shipping_address_ids": [shipping_address_id]
        }
        client.post(f"/customers/{customer_id}/orders/", json=order_data)

    # Test wrt billing zip code, this time descending
    response = client.get(
        "/analytics/orders/by-zip/", 
        params={
            "is_billing": True,
            "ascending": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["zip_code"] == "98765-4321"
    assert data[0]["order_count"] == 15
    assert data[1]["zip_code"] == "12345-6789"
    assert data[1]["order_count"] == 7

def test_analytics_in_store_most_purchases_hours(test_db):
    # Create test customer first
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
                "zip_code": "12345-6789"
            }
        ]
    }
    customer_response = client.post("/customers/", json=customer_data)
    customer_id = customer_response.json()["id"]
    billing_address_id = customer_response.json()["addresses"][0]["id"]

    # Create 10 orders
    # BEWARE: hour boundary cross may pose issues
    # for now, keeping simple
    for _ in range(10):
        order_data = {
            "order_type": "in_store",
            "total_amount": random.random(),
            "billing_address_id": billing_address_id,
            "shipping_address_ids": []
        }
        client.post(f"/customers/{customer_id}/orders/", json=order_data)

    # Test in-store hours analytics
    response = client.get("/analytics/in-store/hours/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["order_count"] == 10

def test_analytics_in_store_top_5_ordering_customers(test_db):
    # Create 10 customers with varying numbers of in-store orders
    customers = []
    for i in range(10):
        customer_data = {
            "telephone": f"123-456-789{i}",
            "email": f"customer{i}@example.com",
            "first_name": f"Customer{i}",
            "last_name": f"Test{i}",
            "addresses": [
                {
                    "type": "billing",
                    "street": f"{100 + i} Main St",
                    "city": "Test City",
                    "state": "TS",
                    "zip_code": f"1234{i}"
                }
            ]
        }
        customer_response = client.post("/customers/", json=customer_data)
        customers.append({
            "id": customer_response.json()["id"],
            "billing_address_id": customer_response.json()["addresses"][0]["id"],
            "first_name": f"Customer{i}",
            "last_name": f"Test{i}"
        })
    
    # Define the order counts for each customer
    # Top 5 customers should have: 15, 12, 10, 8, 6 orders respectively
    # Bottom 5 customers should have: 5, 4, 3, 2, 1 orders respectively
    order_counts = [15, 12, 10, 8, 6, 5, 4, 3, 2, 1]
    
    # Create orders for each customer according to the planned counts
    for i, customer in enumerate(customers):
        for _ in range(order_counts[i]):
            order_data = {
                "order_type": "in_store",
                "total_amount": 100.0 + random.random(),
                "billing_address_id": customer["billing_address_id"],
                "shipping_address_ids": []
            }
            client.post(f"/customers/{customer['id']}/orders/", json=order_data)
    
    # Test top in-store customers with max orders (should return top 5 by default)
    response = client.get("/analytics/in-store/top-customers/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    
    # Verify the top 5 customers are returned in correct order (descending by order count)
    expected_top_5 = [
        {"customer_id": customers[0]["id"], "first_name": "Customer0", "last_name": "Test0", "order_count": 15},
        {"customer_id": customers[1]["id"], "first_name": "Customer1", "last_name": "Test1", "order_count": 12},
        {"customer_id": customers[2]["id"], "first_name": "Customer2", "last_name": "Test2", "order_count": 10},
        {"customer_id": customers[3]["id"], "first_name": "Customer3", "last_name": "Test3", "order_count": 8},
        {"customer_id": customers[4]["id"], "first_name": "Customer4", "last_name": "Test4", "order_count": 6}
    ]
    
    # Verify each of the top 5 customers
    for i, expected_customer in enumerate(expected_top_5):
        assert data[i]["customer_id"] == expected_customer["customer_id"]
        assert data[i]["first_name"] == expected_customer["first_name"]
        assert data[i]["last_name"] == expected_customer["last_name"]
        assert data[i]["order_count"] == expected_customer["order_count"]
    
    # Verify that the customers are ordered by order_count in descending order
    for i in range(len(data) - 1):
        assert data[i]["order_count"] >= data[i + 1]["order_count"]