from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    Boolean
)

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# PRODUCTS TABLE
class Product(Base):

    __tablename__ = "products"

    product_id = Column(
        String,
        primary_key=True
    )

    product_name = Column(String)

    category = Column(String)

    unit_price = Column(Float)

    supplier_name = Column(String)

# WAREHOUSES / HUBS TABLE
class Warehouse(Base):

    __tablename__ = "warehouses"

    hub_id = Column(
        String,
        primary_key=True
    )

    warehouse_name = Column(String)

    city = Column(String)

    delivery_count = Column(Integer)

    total = Column(Integer)

    pickup_ratio = Column(Float)

    delivery_ratio = Column(Float)

    is_warehouse = Column(Boolean)

    is_delivery_hub = Column(Boolean)

    is_mixed_hub = Column(Boolean)

    rep_dipan_id = Column(String)

    capacity = Column(Integer)

    total_products = Column(Integer)

# INVENTORY TABLE
class Inventory(Base):

    __tablename__ = "inventory"

    inventory_id = Column(
        String,
        primary_key=True
    )

    product_id = Column(
        String,
        ForeignKey("products.product_id")
    )

    hub_id = Column(
        String,
        ForeignKey("warehouses.hub_id")
    )

    rep_dipan_id = Column(String)

    quantity = Column(Integer)

    threshold_limit = Column(Integer)

    last_updated = Column(DateTime)