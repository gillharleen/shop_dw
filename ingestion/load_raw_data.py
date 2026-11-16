import random
from datetime import datetime, timedelta

import psycopg2
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

# Connection details must match docker-compose.yml
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    dbname="shop_dw",
    user="harleengill",
    password="password123",
)
cur = conn.cursor()

# ------------------------------------------------------------
# 1. Create the raw schema and tables (safe to run many times)
# ------------------------------------------------------------
cur.execute("""
create schema if not exists raw;

drop table if exists raw.order_items;
drop table if exists raw.orders;
drop table if exists raw.products;
drop table if exists raw.customers;

create table raw.customers (
    customer_id int primary key,
    full_name   text,
    email       text,
    city        text,
    created_at  timestamp,
    loaded_at   timestamp default now()
);

create table raw.products (
    product_id   int primary key,
    product_name text,
    category     text,
    price        numeric(10,2),
    loaded_at    timestamp default now()
);

create table raw.orders (
    order_id    int primary key,
    customer_id int,
    order_date  date,
    status      text,
    updated_at  timestamp,
    loaded_at   timestamp default now()
);

create table raw.order_items (
    order_item_id int primary key,
    order_id      int,
    product_id    int,
    quantity      int,
    unit_price    numeric(10,2),
    loaded_at     timestamp default now()
);
""")

# ------------------------------------------------------------
# 2. Generate fake data
# ------------------------------------------------------------
categories = ["Skincare", "Haircare", "Wellness", "Home"]
now = datetime.now()


def messy_email(email):
    # Real raw data is often untidy: mixed case or extra spaces.
    # Silver will clean this on Day 2.
    return random.choice([email, email.upper(), f"  {email}  "])


customers = [
    (
        i,
        fake.name(),
        messy_email(fake.email()),
        fake.city(),
        now - timedelta(days=random.randint(100, 400)),
    )
    for i in range(1, 101)
]

products = [
    (
        i,
        f"{fake.word().title()} {random.choice(['Cream', 'Oil', 'Soap', 'Serum'])}",
        random.choice(categories),
        round(random.uniform(5, 100), 2),
    )
    for i in range(1, 21)
]
price_of = {p[0]: p[3] for p in products}

orders = []
order_items = []
item_id = 1
for order_id in range(1, 301):
    order_date = (now - timedelta(days=random.randint(0, 90))).date()
    orders.append((
        order_id,
        random.randint(1, 100),
        order_date,
        random.choice(["completed", "completed", "completed", "shipped", "cancelled"]),
        datetime.combine(order_date, datetime.min.time()),
    ))
    for _ in range(random.randint(1, 4)):
        product_id = random.randint(1, 20)
        order_items.append((
            item_id,
            order_id,
            product_id,
            random.randint(1, 5),
            price_of[product_id],
        ))
        item_id += 1

# ------------------------------------------------------------
# 3. Insert into Postgres
# ------------------------------------------------------------
cur.executemany(
    "insert into raw.customers (customer_id, full_name, email, city, created_at) "
    "values (%s, %s, %s, %s, %s)",
    customers,
)
cur.executemany(
    "insert into raw.products (product_id, product_name, category, price) "
    "values (%s, %s, %s, %s)",
    products,
)
cur.executemany(
    "insert into raw.orders (order_id, customer_id, order_date, status, updated_at) "
    "values (%s, %s, %s, %s, %s)",
    orders,
)
cur.executemany(
    "insert into raw.order_items (order_item_id, order_id, product_id, quantity, unit_price) "
    "values (%s, %s, %s, %s, %s)",
    order_items,
)

conn.commit()
cur.close()
conn.close()

print(
    f"Loaded {len(customers)} customers, {len(products)} products, "
    f"{len(orders)} orders, {len(order_items)} order items."
)
