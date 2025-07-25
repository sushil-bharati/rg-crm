from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime
from .models import OrderType, AddressType

class AddressBase(BaseModel):
    type: AddressType
    street: str
    city: str
    state: str
    zip_code: str

class AddressCreate(AddressBase):
    pass

class Address(AddressBase):
    id: int
    customer_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CustomerBase(BaseModel):
    telephone: str
    email: EmailStr
    first_name: str
    last_name: str

class CustomerCreate(CustomerBase):
    addresses: List[AddressCreate]

class Customer(CustomerBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    addresses: List[Address] = []

    model_config = ConfigDict(from_attributes=True)

class OrderBase(BaseModel):
    order_type: OrderType
    total_amount: float

class OrderCreate(OrderBase):
    billing_address_id: int
    shipping_address_ids: List[int] = []

class Order(OrderBase):
    id: int
    customer_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    billing_address: Address
    shipping_addresses: List[Address] = []

    model_config = ConfigDict(from_attributes=True)

class CustomerOrderHistory(BaseModel):
    customer: Customer
    orders: List[Order]

class ZipCodeAnalytics(BaseModel):
    zip_code: str
    order_count: int

class InStoreAnalytics(BaseModel):
    hour: int
    order_count: int

class TopCustomer(BaseModel):
    customer_id: int
    first_name: str
    last_name: str
    order_count: int 