import pandas as pd

orders = pd.read_csv("data/processed/orders_clean.csv")
items = pd.read_csv("data/processed/order_items_clean.csv")
products = pd.read_csv("data/processed/products_clean.csv")

df = items.merge(products, on="product_id", how="left")
df = df.merge(orders, on="order_id", how="left")

df["amount"] = df["quantity"] * df["price"]

result = (
    df.groupby("category")["amount"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)

print(result)
result.to_csv("C:/reports/category_sales.csv", index=False)
