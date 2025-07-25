from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from . import crud, models, schemas
from .database import engine, get_db

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="RG CRM API")

@app.post("/customers/", response_model=schemas.Customer)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    # Check for duplicate email
    db_customer = crud.get_customer_by_email(db, email=customer.email)
    if db_customer:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check for duplicate telephone
    db_customer = crud.get_customer_by_telephone(db, telephone=customer.telephone)
    if db_customer:
        raise HTTPException(status_code=400, detail="Telephone already registered")
    
    return crud.create_customer(db=db, customer=customer)

@app.post("/customers/{customer_id}/orders/", response_model=schemas.Order)
def create_order(
    customer_id: int,
    order: schemas.OrderCreate,
    db: Session = Depends(get_db)
):
    return crud.create_order(db=db, customer_id=customer_id, order=order)

@app.get("/customers/history/", response_model=Optional[schemas.CustomerOrderHistory])
def get_customer_order_history(
    identifier: str,
    is_email: bool = True,
    db: Session = Depends(get_db)
):
    history = crud.get_customer_order_history(
        db,
        customer_identifier=identifier,
        is_email=is_email
    )
    if not history:
        raise HTTPException(status_code=404, detail="Customer not found")
    return history

@app.get("/analytics/orders/by-zip/", response_model=List[schemas.ZipCodeAnalytics])
def get_orders_by_zip(
    is_billing: bool = True,
    ascending: bool = True,
    db: Session = Depends(get_db)
):
    return crud.get_orders_by_zip_code(
        db,
        is_billing=is_billing,
        ascending=ascending
    )

@app.get("/analytics/in-store/hours/", response_model=List[schemas.InStoreAnalytics])
def get_in_store_hours(db: Session = Depends(get_db)):
    return crud.get_in_store_purchase_hours(db)

@app.get("/analytics/in-store/top-customers/", response_model=List[schemas.TopCustomer])
def get_top_in_store_customers(db: Session = Depends(get_db)):
    return crud.get_top_in_store_customers(db) 