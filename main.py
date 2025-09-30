from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from db import get_session
from datetime import date, timedelta
from sqlalchemy import func, cast, Integer, case
from models import get_db_model
from collections import Counter
import io
import csv

app = FastAPI()


@app.get("/products/by_name")
def products_by_name(
    db_name: str = Query(..., description="Database name to connect"),
    launch_start_days: int = Query(..., description="Min days since launch"),
    launch_end_days: int = Query(..., description="Max days since launch")
):
    import traceback
    try:
        with get_session(db_name) as session:
            today = date.today()
            Item, Sale, ViewsAtc = get_db_model(db_name)
            group_column = Item.Category if hasattr(Item, "Category") else Item.Product_Type

            # Query all items in date range
            items_query = (
                session.query(
                    Item.Item_Id,
                    Item.Item_Name,
                    Item.Item_Type,
                    group_column,
                    Item.launch_date,
                    cast(Item.Current_Stock, Integer).label("current_stock"),
                    cast(Item.Sale_Price, Integer).label("sale_price"),
                    Item.Size if hasattr(Item, "Size") else None
                )
                .filter(func.datediff(func.current_date(), Item.launch_date)
                        .between(launch_start_days, launch_end_days))
                .all()
            )

            # Precompute total quantity sold per Item_Id
            all_item_ids = [item.Item_Id for item in items_query]
            qty_sold_map = {
                row.Item_Id: row.total_qty
                for row in session.query(
                    Sale.Item_Id,
                    func.coalesce(func.sum(Sale.Quantity), 0).label("total_qty")
                ).filter(Sale.Item_Id.in_(all_item_ids)).group_by(Sale.Item_Id).all()
            }

            # Total views & ATC per Item_Name + category
            views_atc_map = {}
            views_rows = (
                session.query(
                    Item.Item_Name,
                    group_column.label("category"),
                    func.coalesce(func.sum(ViewsAtc.Items_Viewed), 0).label("total_views"),
                    func.coalesce(func.sum(ViewsAtc.Items_Addedtocart), 0).label("total_atc")
                )
                .join(ViewsAtc, ViewsAtc.Item_Id == Item.Item_Id)
                .filter(Item.Item_Id.in_(all_item_ids))
                .group_by(Item.Item_Name, group_column)
                .all()
            )
            for row in views_rows:
                views_atc_map[(row.Item_Name, row.category)] = {
                    "total_views": row.total_views,
                    "total_atc": row.total_atc
                }

            # Size-level data per Item_Id
            size_data_map = {}
            size_rows = (
                session.query(
                    Item.Item_Id,
                    Item.Size if hasattr(Item, "Size") else None,
                    cast(Item.Current_Stock, Integer).label("current_stock"),
                    func.coalesce(func.sum(Sale.Quantity), 0).label("qty_sold"),
                    func.coalesce(
                        case(
                            (func.count(Sale.Date) > 1,
                             (func.datediff(func.max(Sale.Date), func.min(Sale.Date)) /
                              (func.count(Sale.Date) - 1))
                             ),
                            else_=0
                        ), 0
                    ).label("avg_days_between_sales"),
                    func.coalesce(func.datediff(func.current_date(), func.max(Sale.Date)), 0).label("days_since_last_sold")
                )
                .outerjoin(Sale, Sale.Item_Id == Item.Item_Id)
                .filter(Item.Item_Id.in_(all_item_ids))
                .group_by(Item.Item_Id, Item.Size if hasattr(Item, "Size") else Item.Item_Id, Item.Current_Stock)
                .all()
            )
            for row in size_rows:
                item_id = row[0]
                if item_id not in size_data_map:
                    size_data_map[item_id] = []
                size_data_map[item_id].append(row[1:])

            # Group by item_name + product_type
            grouped_map = {}
            for item in items_query:
                item_name = item.Item_Name
                product_type = getattr(item, group_column.key) if hasattr(item, group_column.key) else None
                key = (item_name, product_type)
                if key not in grouped_map:
                    grouped_map[key] = {
                        "item_type": item.Item_Type,
                        "launch_date": item.launch_date,
                        "variants": []
                    }
                grouped_map[key]["variants"].append({
                    "item_id": item.Item_Id,
                    "size": item.Size if hasattr(item, "Size") else None,
                    "current_stock": item.current_stock,
                    "sale_price": item.sale_price,
                    "qty_sold": qty_sold_map.get(item.Item_Id, 0),
                    "size_data": size_data_map.get(item.Item_Id, [])
                })

            # Build results
            results = []
            for key, group in grouped_map.items():
                item_name, product_type = key
                item_type = group["item_type"]
                launch_date = group["launch_date"]
                variants = group["variants"]

                total_current_stock = sum(v["current_stock"] for v in variants)
                sale_price_counter = Counter([v["sale_price"] for v in variants])
                sale_price = sale_price_counter.most_common(1)[0][0]
                total_quantity_sold = sum(v["qty_sold"] for v in variants)
                views_data = views_atc_map.get((item_name, product_type), {"total_views": 0, "total_atc": 0})
                total_views = views_data["total_views"]
                total_atc = views_data["total_atc"]

                # Size summary
                all_size_data = []
                for v in variants:
                    all_size_data.extend(v["size_data"])
                total_variants = len(all_size_data)
                variants_in_stock = sum(1 for sd in all_size_data if sd[1] > 0)
                sizewise_list = [
                    {
                        "size": sd[0],
                        "item_id": v["item_id"],
                        "variant_stock": sd[1],
                        "variant_quantity_sold": sd[2],
                        "average_days_between_sales": round(sd[3] or 0, 2),
                        "days_since_last_sold": sd[4]
                    }
                    for v in variants for sd in v["size_data"]
                ]

                day_since_launch = (today - launch_date).days if launch_date else None
                last_sale_days_ago = min([sv["days_since_last_sold"] for sv in sizewise_list if sv["days_since_last_sold"] is not None], default=None)
                if last_sale_days_ago is not None and total_current_stock == 0:
                    last_sale_date = today - timedelta(days=last_sale_days_ago)
                    days_active = (last_sale_date - launch_date).days if launch_date and last_sale_date else day_since_launch
                else:
                    days_active = day_since_launch
                total_stock_percentage_sold = round((total_quantity_sold / (total_quantity_sold + total_current_stock)) * 100, 2) if (total_quantity_sold + total_current_stock) else 0
                per_day_qty_average = round((total_quantity_sold / days_active), 2) if days_active else 0
                projected_days_to_sell_out = round((total_current_stock / per_day_qty_average), 2) if per_day_qty_average else 0

                results.append({
                    "item_name": item_name,
                    "item_type": item_type,
                    "product_type": product_type,
                    "day_since_launch": day_since_launch,
                    "current_stock": total_current_stock,
                    "sale_price": sale_price,
                    "total_quantity_sold": total_quantity_sold,
                    "total_views": total_views,
                    "total_atc": total_atc,
                    "total_stock_percentage_sold": total_stock_percentage_sold,
                    "projected_days_to_sell_out": projected_days_to_sell_out,
                    "per_day_qty_average": per_day_qty_average,
                    "size_summary": {
                        "size": f"'{variants_in_stock}/{total_variants}",
                        "sizewise": sizewise_list
                    }
                })

            return {
                "status": "Success",
                "database": db_name,
                "launch_start_days": launch_start_days,
                "launch_end_days": launch_end_days,
                "today": str(today),
                "products": results
            }
    except Exception as e:
        return {
            "status": "Connection failed",
            "database": db_name,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


def fetch_products(session, db_name: str, launch_start_days: int, launch_end_days: int):
    today = date.today()

    Item, Sale, ViewsAtc = get_db_model(db_name)

    group_column = Item.Category if hasattr(Item, "Category") else Item.Product_Type

    grouped_items = (
        session.query(
            Item.Item_Id,
            Item.Item_Name,
            Item.Item_Type,
            group_column,
            Item.launch_date,
            cast(Item.Current_Stock, Integer).label("current_stock"),
            cast(Item.Sale_Price, Integer).label("sale_price"),
        )
        .filter(func.datediff(func.current_date(), Item.launch_date)
                .between(launch_start_days, launch_end_days))
        .all()
    )

    item_ids = [item.Item_Id for item in grouped_items]

    qty_sold_map = {
        row.Item_Id: row.total_qty
        for row in session.query(
            Sale.Item_Id,
            func.coalesce(func.sum(Sale.Quantity), 0).label("total_qty")
        )
        .filter(Sale.Item_Id.in_(item_ids))
        .group_by(Sale.Item_Id)
        .all()
    }

  
    views_atc_map = {}
    views_rows = (
        session.query(
            Item.Item_Name,
            group_column.label("category"),
            func.coalesce(func.sum(ViewsAtc.Items_Viewed), 0).label("total_views"),
            func.coalesce(func.sum(ViewsAtc.Items_Addedtocart), 0).label("total_atc")
        )
        .join(ViewsAtc, ViewsAtc.Item_Id == Item.Item_Id)
        .filter(Item.Item_Id.in_(item_ids))
        .group_by(Item.Item_Name, group_column)
        .all()
    )
    for row in views_rows:
        views_atc_map[(row.Item_Name, row.category)] = {
            "total_views": row.total_views,
            "total_atc": row.total_atc
        }

 
    size_data_map = {}
    size_rows = (
        session.query(
            Item.Item_Id,
            Item.Size if hasattr(Item, "Size") else None,
            cast(Item.Current_Stock, Integer),
            func.coalesce(func.sum(Sale.Quantity), 0).label("qty_sold"),
            # avg days between sales
            func.coalesce(
                case(
                    (func.count(Sale.Date) > 1,
                     (func.datediff(func.max(Sale.Date), func.min(Sale.Date)) /
                      (func.count(Sale.Date) - 1))
                    ),
                    else_=0
                ), 0
            ).label("avg_days_between_sales"),
            func.coalesce(func.datediff(func.current_date(), func.max(Sale.Date)), 0).label("days_since_last_sold")
        )
        .outerjoin(Sale, Sale.Item_Id == Item.Item_Id)
        .filter(Item.Item_Id.in_(item_ids))
        .group_by(Item.Item_Id, Item.Size if hasattr(Item, "Size") else Item.Item_Id, Item.Current_Stock)
        .all()
    )
    for row in size_rows:
        item_id = row[0]
        if item_id not in size_data_map:
            size_data_map[item_id] = []
        size_data_map[item_id].append(row[1:])

   
    variants_map = {}
    for item in grouped_items:
        item_name = item.Item_Name
        product_type = getattr(item, group_column.key) if hasattr(item, group_column.key) else None
        key = (item_name, product_type)
        if key not in variants_map:
            variants_map[key] = []
        variants_map[key].append(item.Item_Id)

   
    results = []
    for item in grouped_items:
        item_id = item.Item_Id
        item_name = item.Item_Name
        item_type = item.Item_Type
        product_type = getattr(item, group_column.key) if hasattr(item, group_column.key) else None
        launch_date = item.launch_date
        total_current_stock = item.current_stock
        sale_price = item.sale_price

        # Total sold
        total_quantity_sold = qty_sold_map.get(item_id, 0)

        # Total views & ATC
        views_data = views_atc_map.get((item_name, product_type), {"total_views":0,"total_atc":0})
        total_views = views_data["total_views"]
        total_atc = views_data["total_atc"]

        # Size-level
        all_variant_ids = variants_map.get((item_name, product_type), [])
        all_size_data = []
        for vid in all_variant_ids:
            all_size_data.extend(size_data_map.get(vid, []))
        total_variants = len(all_size_data)
        variants_in_stock = sum(1 for sd in all_size_data if sd[1] > 0)

        # For this item_id, show only its own sizewise_list
        size_data = size_data_map.get(item_id, [])
        sizewise_list = [
            {
                "size": sd[0],
                "variant_stock": sd[1],
                "variant_quantity_sold": sd[2],
                "average_days_between_sales": round(sd[3] or 0, 2),
                "days_since_last_sold": sd[4]
            }
            for sd in size_data
        ]

        day_since_launch = (today - launch_date).days if launch_date else None
       
        last_sale_days_ago = min([v["days_since_last_sold"] for v in sizewise_list if v["days_since_last_sold"] is not None], default=None)
        if last_sale_days_ago is not None and total_current_stock == 0:
            last_sale_date = today - timedelta(days=last_sale_days_ago)
            days_active = (last_sale_date - launch_date).days if launch_date and last_sale_date else day_since_launch
        else:
            days_active = day_since_launch
        
        total_stock_percentage_sold = round((total_quantity_sold / (total_quantity_sold + total_current_stock)) * 100, 2) if (total_quantity_sold + total_current_stock) else 0
        per_day_qty_average = round((total_quantity_sold / days_active), 2) if days_active else 0
        projected_days_to_sell_out = round((total_current_stock / per_day_qty_average), 2) if per_day_qty_average else 0

        results.append({
            "item_id": item_id,
            "item_name": item_name,
            "item_type": item_type,
            "product_type": product_type,
            "day_since_launch": day_since_launch,
            "current_stock": total_current_stock,
            "sale_price": sale_price,
            "total_quantity_sold": total_quantity_sold,
            "total_views": total_views,
            "total_atc": total_atc,
            "total_stock_percentage_sold": total_stock_percentage_sold,
            "projected_days_to_sell_out": projected_days_to_sell_out,
            "per_day_qty_average": per_day_qty_average,
            "size_summary": {
                "size": f"'{variants_in_stock}/{total_variants}",
                "sizewise": sizewise_list
            }
        })

    return today, results


@app.get("/products")
def products(
    db_name: str = Query(..., description="Database name to connect"),
    launch_start_days: int = Query(..., description="Min days since launch"),
    launch_end_days: int = Query(..., description="Max days since launch")
):
    import traceback
    try:
        with get_session(db_name) as session:
            today, results = fetch_products(session, db_name, launch_start_days, launch_end_days)
    except Exception as e:
        return {
            "status": "Connection failed",
            "database": db_name,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

    return {
        "status":"Success",
        "database": db_name,
        "launch_start_days": launch_start_days,
        "launch_end_days": launch_end_days,
        "today": str(today),
        "products": results
    }


@app.get("/products/csv")
def products_csv(
    db_name: str = Query(..., description="Database name to connect"),
    launch_start_days: int = Query(..., description="Min days since launch"),
    launch_end_days: int = Query(..., description="Max days since launch")
):
    import traceback
    try:
        with get_session(db_name) as session:
            today, results = fetch_products(session, db_name, launch_start_days, launch_end_days)
    except Exception as e:
        return {
            "status": "Connection failed",
            "database": db_name,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "item_id","item_name","item_type","product_type",
        "day_since_launch","current_stock","sale_price",
        "total_quantity_sold","total_views","total_atc",
        "total_stock_percentage_sold","projected_days_to_sell_out","per_day_qty_average",
        "size_summary","size","variant_stock","variant_quantity_sold",
        "average_days_between_sales","days_since_last_sold"
    ])

    for row in results:
        size_summary_text = f"{row['size_summary']['size']}"
        for variant in row["size_summary"]["sizewise"]:
            writer.writerow([
                row["item_id"],
                row["item_name"],
                row["item_type"],
                row["product_type"],
                row["day_since_launch"],
                row["current_stock"],
                row["sale_price"],
                row["total_quantity_sold"],
                row["total_views"],
                row["total_atc"],
                row["total_stock_percentage_sold"],
                row["projected_days_to_sell_out"],
                row["per_day_qty_average"],
                size_summary_text,
                variant["size"],
                variant["variant_stock"],
                variant["variant_quantity_sold"],
                variant["average_days_between_sales"],
                variant["days_since_last_sold"]
            ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=products_{today}.csv"}
    )