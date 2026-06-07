from chatbot import env_setup  # noqa: F401
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

TABLE products
- product_id
- product_name
- category
- unit_price
- supplier_name

TABLE warehouses
- hub_id
- warehouse_name
- city
- delivery_count
- total
- pickup_ratio
- delivery_ratio
- is_warehouse
- is_delivery_hub
- is_mixed_hub
- rep_dipan_id
- capacity
- total_products

TABLE inventory
- inventory_id
- product_id
- hub_id
- rep_dipan_id
- quantity
- threshold_limit
- last_updated

Relationships:
- inventory.product_id references products.product_id
- inventory.hub_id references warehouses.hub_id
- inventory.rep_dipan_id references warehouses.rep_dipan_id

Primary Keys:
- products.product_id is the primary key of products
- warehouses.hub_id is the primary key of warehouses
- inventory.inventory_id is the primary key of inventory

Join Rules:
- Join inventory with products using:
  inventory.product_id = products.product_id

- Join inventory with warehouses using:
  inventory.hub_id = warehouses.hub_id

Rules:
- Return ONLY SQL
- Use PostgreSQL syntax
- Use ILIKE for product name searches
- Do not explain anything
- Always use JOINs where necessary
- NEVER create columns not present in schema
- NEVER use warehouse_id
- Use only the exact column names provided

Aliases:
- products → p
- warehouses → w
- inventory → i

Semantic Rules:
- Product searches should use:
  products.product_name ILIKE '%value%'

Examples:
- "MacBook" → ILIKE '%MacBook%'
- "iPhone" → ILIKE '%iPhone%'
- "AirPods" → ILIKE '%AirPods%'

Aggregation Rules:
- Questions asking "how many units" should use:
  SUM(i.quantity)

- Questions asking "low inventory" should use:
  i.quantity < i.threshold_limit

- Questions asking "top stocked products" should sort by:
  i.quantity DESC

- Questions asking "highest inventory city" should aggregate using:
  GROUP BY w.city

Human Readability Rules:
- Prefer warehouse_name instead of hub_id in outputs
- Prefer product_name instead of product_id
- Prefer city names in grouped responses
- Internal IDs should only be used if explicitly requested

Examples:
- BAD: W028
- GOOD: Shanghai_Hub_28
"""

# DOMAIN KEYWORDS
allowed_keywords = [

    # Inventory Terms
    "inventory",
    "stock",
    "quantity",
    "units",
    "available",
    "remaining",
    "restock",
    "threshold",
    "low stock",
    "inventory level",

    # Warehouse / Hub Terms
    "warehouse",
    "warehouses",
    "hub",
    "hubs",
    "storage",

    # Product Terms
    "product",
    "products",
    "device",
    "devices",
    "category",

    # Apple Products
    "iphone",
    "macbook",
    "ipad",
    "airpods",
    "apple watch",
    "watch",
    "vision pro",
    "homepod",
    "apple tv",
    "magic keyboard",
    "magic mouse",
    "apple pencil",
    "magsafe",

    # Inventory Actions
    "stored",
    "stocked",
    "supply",
    "availability",

    # Analytics
    "highest",
    "lowest",
    "top",
    "least",
    "average",
    "most",
    "total",
    "sum",

    # Cities
    "city",
    "shanghai",
    "hangzhou",
    "chongqing",
    "beijing",
    "guangzhou",
    "shenzhen",

    # Business Queries
    "below threshold",
    "critical",
    "inventory status",
    "inventory report",
    "stock status"
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