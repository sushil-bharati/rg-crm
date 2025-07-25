from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from . import models, schemas
from typing import List, Optional

def get_customer_by_email(db: Session, email: str) -> Optional[models.Customer]:
    ''' Find customer with the given email '''
    return db.query(models.Customer).filter(models.Customer.email == email).first()

def get_customer_by_telephone(db: Session, telephone: str) -> Optional[models.Customer]:
    ''' Find customer with the given telephone number '''
    return db.query(models.Customer).filter(models.Customer.telephone == telephone).first()

def create_customer(db: Session, customer: schemas.CustomerCreate) -> models.Customer:
    ''' Create a customer entry along with their addresses '''
    db_customer = models.Customer(
        telephone=customer.telephone,
        email=customer.email,
        first_name=customer.first_name,
        last_name=customer.last_name
    )
    db.add(db_customer)
    db.flush()  # Get the customer ID without committing

    # Create addresses: A customer can have multiple addresses
    for address in customer.addresses:
        db_address = models.Address(
            customer_id=db_customer.id,
            type=address.type,
            street=address.street,
            city=address.city,
            state=address.state,
            zip_code=address.zip_code
        )
        db.add(db_address)

    db.commit()
    db.refresh(db_customer)
    return db_customer

def create_order(db: Session, customer_id: int, order: schemas.OrderCreate) -> models.Order:
    ''' Create an order entry along with their shipping addresses '''
    db_order = models.Order(
        customer_id=customer_id,
        order_type=order.order_type,
        total_amount=order.total_amount,
        billing_address_id=order.billing_address_id
    )
    db.add(db_order)
    db.flush()

    # Add shipping addresses: An order can go to multiple shipping addresses
    if order.shipping_address_ids:
        shipping_addresses = db.query(models.Address).filter(
            models.Address.id.in_(order.shipping_address_ids)
        ).all()
        db_order.shipping_addresses.extend(shipping_addresses)

    db.commit()
    db.refresh(db_order)
    return db_order

def get_customer_order_history(
    db: Session,
    customer_identifier: str,
    is_email: bool = True
) -> Optional[schemas.CustomerOrderHistory]:
    # TODO: It should also provide billing addresses and shipping addresses
    ''' Given telephone or email, get order history along with their bill/shipping addresses'''
    if is_email:
        customer = get_customer_by_email(db, customer_identifier)
    else:
        customer = get_customer_by_telephone(db, customer_identifier)

    if not customer:
        return None

    return schemas.CustomerOrderHistory(
        customer=customer,
        orders=customer.orders
    )

def get_orders_by_zip_code(
    db: Session,
    is_billing: bool = True,
    ascending: bool = True
) -> List[schemas.ZipCodeAnalytics]:
    ''' Total count of orders aggregrated by bill/shipping zip code '''
    if is_billing:
        query = db.query(
            models.Address.zip_code,
            func.count(models.Order.id).label('order_count')
        ).join(
            models.Order,
            models.Address.id == models.Order.billing_address_id
        ).filter(
            models.Address.type == models.AddressType.BILLING
        )
    else:
        query = db.query(
            models.Address.zip_code,
            func.count(models.Order.id).label('order_count')
        ).join(
            models.order_shipping_addresses,
            models.Address.id == models.order_shipping_addresses.c.address_id
        ).join(
            models.Order,
            models.order_shipping_addresses.c.order_id == models.Order.id
        ).filter(
            models.Address.type == models.AddressType.SHIPPING
        )

    query = query.group_by(models.Address.zip_code)
    
    if ascending:
        query = query.order_by(func.count(models.Order.id).asc())
    else:
        query = query.order_by(func.count(models.Order.id).desc())

    results = query.all()
    return [
        schemas.ZipCodeAnalytics(zip_code=zip_code, order_count=count)
        for zip_code, count in results
    ]

def get_in_store_purchase_hours(db: Session) -> List[schemas.InStoreAnalytics]:
    ''' Time of day where most in-store purchases are made '''
    results = db.query(
        extract('hour', models.Order.created_at).label('hour'),
        func.count(models.Order.id).label('order_count')
    ).filter(
        models.Order.order_type == models.OrderType.IN_STORE
    ).group_by(
        extract('hour', models.Order.created_at)
    ).order_by(
        func.count(models.Order.id).desc()
    ).all()

    return [
        schemas.InStoreAnalytics(hour=hour, order_count=count)
        for hour, count in results
    ]

def get_top_in_store_customers(db: Session, limit: int = 5) -> List[schemas.TopCustomer]:
    ''' Top-k customer with most in-store purchases '''
    results = db.query(
        models.Customer.id,
        models.Customer.first_name,
        models.Customer.last_name,
        func.count(models.Order.id).label('order_count')
    ).join(
        models.Order
    ).filter(
        models.Order.order_type == models.OrderType.IN_STORE
    ).group_by(
        models.Customer.id,
        models.Customer.first_name,
        models.Customer.last_name
    ).order_by(
        func.count(models.Order.id).desc()
    ).limit(limit).all()

    return [
        schemas.TopCustomer(
            customer_id=id,
            first_name=first_name,
            last_name=last_name,
            order_count=count
        )
        for id, first_name, last_name, count in results
    ]