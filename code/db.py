"""Synthetic retail database (no real personal data)."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "retail.db"

CUSTOMERS = [
    (1, "Aarav Mehta", "Delhi", "2024-01-10"), (2, "Diya Sharma", "Mumbai", "2024-02-14"),
    (3, "Rohan Gupta", "Delhi", "2024-03-05"), (4, "Sana Khan", "Bengaluru", "2024-04-20"),
    (5, "Vikram Rao", "Hyderabad", "2024-06-11"), (6, "Meera Nair", "Kochi", "2024-08-02"),
    (7, "Kabir Singh", "Delhi", "2024-09-15"), (8, "Ananya Iyer", "Chennai", "2024-11-30"),
]
PRODUCTS = [
    (1, "Wireless Mouse", "Electronics", 899.0), (2, "Bluetooth Speaker", "Electronics", 2499.0),
    (3, "Laptop Stand", "Electronics", 1599.0), (4, "Python Cookbook", "Books", 650.0),
    (5, "SQL Handbook", "Books", 550.0), (6, "Desk Lamp", "Home", 1200.0),
    (7, "Water Bottle", "Home", 450.0), (8, "Yoga Mat", "Fitness", 999.0),
]
ORDERS = [  # (order_id, customer_id, order_date)
    (1, 1, "2025-01-15"), (2, 2, "2025-02-03"), (3, 1, "2025-03-22"), (4, 3, "2025-04-10"),
    (5, 4, "2025-05-18"), (6, 2, "2025-06-25"), (7, 5, "2025-07-07"), (8, 1, "2025-08-19"),
    (9, 6, "2025-09-12"), (10, 3, "2025-10-05"), (11, 7, "2025-10-28"), (12, 2, "2025-11-14"),
    (13, 4, "2025-12-02"), (14, 1, "2025-12-20"), (15, 5, "2026-01-08"),
]
ITEMS = [  # (order_id, product_id, quantity)
    (1, 1, 1), (1, 4, 2), (2, 2, 1), (3, 5, 1), (3, 7, 2), (4, 6, 1), (5, 3, 1), (5, 1, 1),
    (6, 8, 1), (7, 2, 1), (7, 4, 1), (8, 7, 3), (9, 4, 1), (9, 5, 1), (10, 1, 2),
    (11, 8, 1), (11, 7, 1), (12, 3, 1), (13, 6, 1), (13, 5, 1), (14, 2, 1), (14, 1, 1), (15, 8, 2),
]

SCHEMA_PLAIN = """CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, city TEXT, signup_date TEXT);
CREATE TABLE products (product_id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(customer_id), order_date TEXT, total_amount REAL);
CREATE TABLE order_items (order_id INTEGER REFERENCES orders(order_id), product_id INTEGER REFERENCES products(product_id), quantity INTEGER);"""

SCHEMA_DESCRIBED = """Dialect: SQLite. Dates are TEXT in 'YYYY-MM-DD' format.
customers(customer_id INTEGER PK, name TEXT, city TEXT, signup_date TEXT)
  -- one row per customer; city is the customer's home city
products(product_id INTEGER PK, name TEXT, category TEXT, price REAL)
  -- category is one of: Electronics, Books, Home, Fitness; price in rupees
orders(order_id INTEGER PK, customer_id INTEGER FK -> customers.customer_id, order_date TEXT, total_amount REAL)
  -- one row per order; total_amount is the order's total in rupees
order_items(order_id INTEGER FK -> orders.order_id, product_id INTEGER FK -> products.product_id, quantity INTEGER)
  -- one row per product line inside an order"""


def build_db(path: Path = DB_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript(SCHEMA_PLAIN)
    con.executemany("INSERT INTO customers VALUES (?,?,?,?)", CUSTOMERS)
    con.executemany("INSERT INTO products VALUES (?,?,?,?)", PRODUCTS)
    price = {p[0]: p[3] for p in PRODUCTS}
    totals = {}
    for oid, pid, qty in ITEMS:
        totals[oid] = totals.get(oid, 0) + price[pid] * qty
    con.executemany("INSERT INTO orders VALUES (?,?,?,?)", [(o, c, d, totals[o]) for o, c, d in ORDERS])
    con.executemany("INSERT INTO order_items VALUES (?,?,?)", ITEMS)
    con.commit()
    con.close()
    return path


def run_readonly(sql: str, path: Path = DB_PATH, max_rows: int = 200):
    """Execute on a read-only connection. Returns (columns, rows). Raises sqlite3.Error on failure."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, cur.fetchmany(max_rows)
    finally:
        con.close()


if __name__ == "__main__":
    print("Built", build_db())
