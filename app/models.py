from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Float, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class OrderType(enum.Enum):
    IN_STORE = "in_store"
    ONLINE = "online"

class AddressType(enum.Enum):
    BILLING = "billing"
    SHIPPING = "shipping"

# Association table for order-shipping addresses (many-to-many)
# Each order can have multiple shipping addresses
# Each address can be used in multiple orders
order_shipping_addresses = Table(
    'order_shipping_addresses',
    Base.metadata,
    Column('order_id', Integer, ForeignKey('orders.id')),
    Column('address_id', Integer, ForeignKey('addresses.id'))
)

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    telephone = Column(String, unique=True, index=True) # Ignoring validation for simplicity, indexing for efficient search
    email = Column(String, unique=True, index=True) # Ignoring validation for simplicity, indexing for efficient search
    first_name = Column(String) # Customer may opt out of PII
    last_name = Column(String) # Customer may opt out of PII
    created_at = Column(DateTime(timezone=True), server_default=func.now()) # Bookkeeping: only at first insert
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) # Bookkeeping: every time it is updated

    # Relationships
    addresses = relationship("Address", back_populates="customer")
    orders = relationship("Order", back_populates="customer")

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    type = Column(Enum(AddressType), nullable=False)
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="addresses")
    orders_as_shipping = relationship(
        "Order",
        secondary=order_shipping_addresses,
        back_populates="shipping_addresses"
    )

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_type = Column(Enum(OrderType), nullable=False)
    total_amount = Column(Float, nullable=False)
    billing_address_id = Column(Integer, ForeignKey("addresses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    billing_address = relationship("Address", foreign_keys=[billing_address_id])
    shipping_addresses = relationship(
        "Address",
        secondary=order_shipping_addresses,
        back_populates="orders_as_shipping"
    )