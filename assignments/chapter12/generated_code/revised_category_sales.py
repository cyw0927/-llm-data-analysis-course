import pandas as pd

orders = pd.read_csv("data/processed/orders_clean.csv")
items = pd.read_csv("data/processed/order_items_clean.csv")
products = pd.read_csv("data/processed/products_clean.csv")

assert orders["order_id"].is_unique
assert products["product_id"].is_unique
assert (items["line_total"] == items["quantity"] * items["unit_price"]).all()

completed_orders = orders.loc[orders["order_status"] == "completed", ["order_id"]]
completed_items = items.merge(
    completed_orders, on="order_id", how="inner", validate="many_to_one"
)

merged = completed_items.merge(
    products[["product_id", "category"]],
    on="product_id",
    how="left",
    validate="many_to_one",
    indicator=True,
)
assert (merged["_merge"] == "both").all()
assert merged["category"].notna().all()

result = (
    merged.groupby("category", as_index=False)["line_total"]
    .sum()
    .rename(columns={"line_total": "sales"})
    .sort_values("sales", ascending=False)
)

print(result.to_string(index=False))
print("행 수:", len(completed_items), "합계:", int(result["sales"].sum()))
result.to_csv("output/category_sales.csv", index=False)
