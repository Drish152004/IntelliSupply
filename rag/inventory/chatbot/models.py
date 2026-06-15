from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    UniqueConstraint,
    ForeignKey,
    Text,
    func,
)

from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ============================================================
# PRODUCT CATALOG TABLE
# Supabase table: product_catalog
# One product_id can exist in multiple categories.
# So product_id alone is NOT unique.
# Unique identity = product_id + category
# ============================================================

class ProductCatalog(Base):
    __tablename__ = "product_catalog"

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    product_id = Column(
        String,
        nullable=False,
    )

    category = Column(
        String,
        nullable=False,
    )

    product_name = Column(String)

    product_display_name = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "category",
            name="product_catalog_product_id_category_key",
        ),
    )


# ============================================================
# HUBS TABLE
# Supabase table: hubs
# This replaces old warehouses table.
# Use lat/lng only for actual coordinates.
# Ignore poi_lat/poi_lng for route/map logic.
# ============================================================

class Hub(Base):
    __tablename__ = "hubs"

    hub_id = Column(
        BigInteger,
        primary_key=True,
    )

    hub_name = Column(String)

    city_id = Column(BigInteger)

    poi_lat = Column(Float)
    poi_lng = Column(Float)

    # Use these for actual hub coordinates
    lat = Column(Float)
    lng = Column(Float)

    representative_aoi_id = Column(String)
    representative_typecode = Column(String)

    hub_type = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# PLANNING DATASET TABLE
# Supabase table: planning_dataset
# This replaces old inventory table.
#
# Stock value = inventory_level
# Low stock condition = inventory_level < demand
# Unique time-series identity:
# date + hub_id + product_id + category
# ============================================================

class PlanningDataset(Base):
    __tablename__ = "planning_dataset"

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    date = Column(Date, nullable=False)

    hub_id = Column(
        BigInteger,
        ForeignKey("hubs.hub_id"),
        nullable=False,
    )

    product_id = Column(
        String,
        nullable=False,
    )

    category = Column(
        String,
        nullable=False,
    )

    inventory_level = Column(Integer)

    units_sold = Column(Integer)

    units_ordered = Column(Integer)

    price = Column(Float)

    discount = Column(Float)

    weather_condition = Column(String)

    promotion = Column(Boolean)

    competitor_pricing = Column(Float)

    seasonality = Column(String)

    epidemic = Column(Boolean)

    demand = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "date",
            "hub_id",
            "product_id",
            "category",
            name="planning_dataset_date_hub_product_category_key",
        ),
    )