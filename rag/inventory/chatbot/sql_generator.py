import env_setup  # noqa: F401
import os
from openai import OpenAI

# NVIDIA CLIENT
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

# SYSTEM PROMPT
SYSTEM_PROMPT = """
You are an expert PostgreSQL assistant.

Generate ONLY SQL queries.

Database schema:

TABLE planning_dataset
- id
- date
- hub_id
- product_id
- category
- inventory_level
- units_sold
- units_ordered
- price
- discount
- weather_condition
- promotion
- competitor_pricing
- seasonality
- epidemic
- demand
- created_at

TABLE product_catalog
- id
- product_id
- category
- product_name
- product_display_name
- created_at

TABLE hubs
- hub_id
- hub_name
- city_id
- poi_lat
- poi_lng
- lat
- lng
- representative_aoi_id
- representative_typecode
- hub_type
- created_at

Relationships:
- planning_dataset.hub_id references hubs.hub_id
- planning_dataset.product_id + planning_dataset.category references product_catalog.product_id + product_catalog.category

Primary Keys:
- planning_dataset.id is the primary key of planning_dataset
- product_catalog.id is the primary key of product_catalog
- hubs.hub_id is the primary key of hubs

Unique Keys:
- planning_dataset has unique key:
  date + hub_id + product_id + category

- product_catalog has unique key:
  product_id + category

Join Rules:
- Join planning_dataset with product_catalog using:
  planning_dataset.product_id = product_catalog.product_id
  AND planning_dataset.category = product_catalog.category

- Join planning_dataset with hubs using:
  planning_dataset.hub_id = hubs.hub_id

Rules:
- Return ONLY SQL
- Use PostgreSQL syntax
- Use ILIKE for product name, category, hub name, and hub type searches
- Do not explain anything
- Always use JOINs where product names or hub names are needed
- NEVER create columns not present in schema
- NEVER use warehouse_id
- NEVER use warehouse_name
- NEVER use inventory table
- NEVER use products table
- NEVER use warehouses table
- Use only the exact column names provided

Aliases:
- planning_dataset → pd
- product_catalog → pc
- hubs → h

Semantic Rules:
- Product name searches should use:
  pc.product_name ILIKE '%value%'

- Product display name searches should use:
  pc.product_display_name ILIKE '%value%'

- Category searches should use:
  pd.category ILIKE '%value%'
  or pc.category ILIKE '%value%'

- Product ID searches should use:
  pd.product_id = 'P0001'

- Hub ID searches should use:
  pd.hub_id = value

- Hub name searches should use:
  h.hub_name ILIKE '%value%'

- Hub type searches should use:
  h.hub_type ILIKE '%value%'

- City ID searches should use:
  h.city_id = value

- Date filters should use:
  pd.date

Business Meaning:
- inventory_level means current stock/inventory level
- units_sold means fulfilled/sold quantity
- units_ordered means replenished/ordered quantity
- demand means actual customer demand
- price means selling price
- discount means discount applied
- competitor_pricing means competitor price
- promotion means promotion flag
- epidemic means external disruption flag
- hub_type describes whether the hub is warehouse, delivery_hub, or mixed_hub
- lat and lng are real-world coordinates of the hub
- poi_lat and poi_lng are original projected coordinates

Aggregation Rules:
- Questions asking "total demand" should use:
  SUM(pd.demand)

- Questions asking "total units sold" should use:
  SUM(pd.units_sold)

- Questions asking "total inventory" or "stock level" should use:
  SUM(pd.inventory_level)

- Questions asking "total units ordered" should use:
  SUM(pd.units_ordered)

- Questions asking "average demand" should use:
  AVG(pd.demand)

- Questions asking "average inventory" should use:
  AVG(pd.inventory_level)

- Questions asking "lost demand" should use:
  SUM(GREATEST(pd.demand - pd.units_sold, 0))

- Questions asking "stockout" should use:
  pd.demand > pd.units_sold

- Questions asking "low inventory" should compare:
  pd.inventory_level < pd.demand

- Questions asking "top demand products" should sort by:
  SUM(pd.demand) DESC

- Questions asking "top sold products" should sort by:
  SUM(pd.units_sold) DESC

- Questions asking "highest inventory products" should sort by:
  SUM(pd.inventory_level) DESC

- Questions asking "lowest inventory products" should sort by:
  SUM(pd.inventory_level) ASC

- Questions asking "demand by category" should group by:
  pd.category

- Questions asking "demand by hub" should group by:
  h.hub_name, pd.hub_id

- Questions asking "demand by hub type" should group by:
  h.hub_type

- Questions asking "demand by city" should group by:
  h.city_id

- Questions asking "daily demand trend" should group by:
  pd.date

- Questions asking "monthly demand" should group by:
  DATE_TRUNC('month', pd.date)

- Questions asking "yearly demand" should group by:
  DATE_TRUNC('year', pd.date)

Human Readability Rules:
- Prefer pc.product_name instead of pd.product_id in outputs
- Prefer pc.product_display_name when available
- Prefer h.hub_name instead of only pd.hub_id in outputs
- Include pd.category when showing product-level results
- Include h.hub_type when the question involves hub type, warehouse, delivery hub, or mixed hub
- Include h.city_id when the question involves city-level grouping
- Internal ids like pd.id and pc.id should only be used if explicitly requested

Important Identity Rule:
- A product is uniquely identified by:
  product_id + category

- Do NOT assume product_id alone is unique across categories.
- When joining product_catalog, always join using both product_id and category.

Examples:
- User asks: demand for Electronics P0001 in Hub 5
  Use:
  pd.hub_id = 5
  AND pd.product_id = 'P0001'
  AND pd.category ILIKE '%Electronics%'

- User asks: inventory for Wireless Router in Hub 0
  Join product_catalog and hubs.
  Use:
  pc.product_name ILIKE '%Wireless Router%'
  AND pd.hub_id = 0

- User asks: inventory in Hub 5
  Join hubs.
  Use:
  pd.hub_id = 5

- User asks: demand in mixed hubs
  Join hubs.
  Use:
  h.hub_type ILIKE '%mixed%'

- User asks: stock in warehouses
  Join hubs.
  Use:
  h.hub_type ILIKE '%warehouse%'

- User asks: stock for P0001
  Use:
  pd.product_id = 'P0001'
  and include category in SELECT because P0001 may exist in multiple categories.

- User asks: top categories by demand
  Use:
  GROUP BY pd.category
  ORDER BY SUM(pd.demand) DESC

- User asks: stockout products
  Use:
  pd.demand > pd.units_sold

- User asks: products with high discount
  Use:
  ORDER BY pd.discount DESC
"""

# DOMAIN KEYWORDS
allowed_keywords = [

    # Planning / Inventory Terms
    "inventory",
    "stock",
    "quantity",
    "units",
    "available",
    "remaining",
    "inventory level",
    "current stock",
    "stock level",
    "ordered",
    "units ordered",
    "sold",
    "units sold",
    "demand",
    "actual demand",
    "lost demand",
    "fulfilled",
    "stockout",
    "out of stock",
    "low inventory",
    "low stock",

    # Hub Terms
    "hub",
    "hubs",
    "hub id",
    "hub_id",
    "hub name",
    "hub type",
    "warehouse",
    "warehouses",
    "delivery hub",
    "delivery_hub",
    "mixed hub",
    "mixed_hub",
    "city",
    "city id",
    "city_id",
    "latitude",
    "longitude",
    "lat",
    "lng",
    "coordinates",
    "location",

    # Product Terms
    "product",
    "products",
    "product id",
    "product_id",
    "product name",
    "category",
    "catalog",
    "product catalog",

    # Categories
    "electronics",
    "clothing",
    "groceries",
    "furniture",
    "toys",

    # Product Names
    "wireless router",
    "bluetooth speaker",
    "smartphone",
    "laptop charger",
    "usb-c cable",
    "smart watch",
    "power bank",
    "led monitor",
    "wireless mouse",
    "keyboard",
    "cotton t-shirt",
    "denim jeans",
    "formal shirt",
    "hoodie",
    "sports jacket",
    "casual shorts",
    "winter sweater",
    "track pants",
    "polo shirt",
    "kurta",
    "leggings",
    "scarf",
    "raincoat",
    "office chair",
    "study table",
    "bookshelf",
    "dining chair",
    "coffee table",
    "bed frame",
    "shoe rack",
    "wardrobe",
    "tv unit",
    "recliner",
    "side table",
    "storage cabinet",
    "rice pack",
    "wheat flour",
    "cooking oil",
    "sugar pack",
    "tea powder",
    "coffee powder",
    "pasta pack",
    "breakfast cereal",
    "milk carton",
    "cheese pack",
    "biscuits",
    "fruit juice",
    "lentils",
    "salt pack",
    "spice mix",
    "noodles pack",
    "butter pack",
    "snack pack",
    "building blocks",
    "puzzle set",
    "toy car",
    "doll set",
    "board game",
    "remote car",
    "soft toy",
    "action figure",
    "coloring kit",
    "learning tablet",
    "toy train",

    # Pricing / Promotion
    "price",
    "unit price",
    "discount",
    "promotion",
    "competitor price",
    "competitor pricing",

    # External Factors
    "weather",
    "weather condition",
    "season",
    "seasonality",
    "epidemic",

    # Time Terms
    "date",
    "daily",
    "monthly",
    "yearly",
    "today",
    "yesterday",
    "last week",
    "last month",
    "last 30 days",
    "last 90 days",
    "trend",

    # Analytics
    "highest",
    "lowest",
    "top",
    "least",
    "average",
    "most",
    "total",
    "sum",
    "count",
    "maximum",
    "minimum",
    "compare",
    "report",
    "status"
]
# SQL GENERATION FUNCTION
def generate_sql(question):

    # DOMAIN VALIDATION
    if not any(
        keyword in question.lower()
        for keyword in allowed_keywords
    ):

        return "INVALID_DOMAIN_QUERY"

    response = client.chat.completions.create(

        model="meta/llama-3.1-8b-instruct",

        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": question
            }
        ],

        temperature=0
    )

    generated_sql = response.choices[0].message.content

    # CLEAN SQL OUTPUT
    generated_sql = str(
        response.choices[0].message.content
    )
    generated_sql = generated_sql.replace(
        "```sql",
        ""
    ).replace(
        "```",
        ""
    ).strip()

    return generated_sql