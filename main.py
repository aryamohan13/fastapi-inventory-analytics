from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
from db import get_connection
from datetime import datetime
import mysql.connector

app = FastAPI()

# Root route → redirect to Swagger docs (hidden from docs UI)
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/products")
def products(
    db_name: str = Query(..., description="Database name to connect"),
    launch_start_days: int = Query(..., description="Min days since launch"),
    launch_end_days: int = Query(..., description="Max days since launch")
):
    today = datetime.today().date()

    # Open DB connection
    conn = get_connection(db_name)
    if not conn:
        return {"status": "❌ Connection failed", "database": db_name}

    cursor = conn.cursor(dictionary=True)

    query = f"""
    WITH grouped_items AS (
        SELECT 
            MIN(i.Item_Id) AS item_id,
            i.Item_Name,
            i.Item_Type,
            i.Category,
            MIN(i.__Launch_Date) AS launch_date,
            SUM(i.Current_Stock) AS total_current_stock,
            MIN(i.Sale_Price) AS sale_price
        FROM items i
        WHERE DATEDIFF(CURRENT_DATE, i.__Launch_Date) 
              BETWEEN {launch_start_days} AND {launch_end_days}
        GROUP BY i.Item_Name, i.Item_Type, i.Category
    ),
    sales_grouped AS (
        SELECT 
            s.Item_Name,
            i.Category,
            SUM(s.Quantity) AS total_quantity_sold,
            IFNULL((
                SELECT AVG(diff_days) 
                FROM (
                    SELECT DATEDIFF(curr.Date, prev.Date) AS diff_days
                    FROM sale curr
                    JOIN sale prev 
                      ON curr.Item_Name = prev.Item_Name
                     AND curr.Date > prev.Date
                     AND curr.Item_Name = s.Item_Name
                ) AS diffs
            ), 0) AS average_days_between_sales
        FROM sale s
        JOIN items i ON i.Item_Id = s.Item_Id
        GROUP BY s.Item_Name, i.Category
    ),
    views_grouped AS (
        SELECT 
            i.Item_Name,
            i.Category,
            SUM(v.Items_Viewed) AS total_views,
            SUM(v.Items_Addedtocart) AS total_atc
        FROM viewsatc v
        JOIN items i ON i.Item_Id = v.Item_Id
        GROUP BY i.Item_Name, i.Category
    )
    SELECT
        gi.item_id,
        gi.Item_Name AS item_name,
        gi.Item_Type AS item_type,
        gi.Category AS product_type,
        DATEDIFF(CURRENT_DATE, gi.launch_date) AS day_since_launch,
        gi.total_current_stock AS current_stock,
        gi.sale_price AS sale_price,
        IFNULL(sg.total_quantity_sold,0) AS total_quantity_sold,
        ROUND(
            (IFNULL(sg.total_quantity_sold,0) / 
             (gi.total_current_stock + IFNULL(sg.total_quantity_sold,0)))*100,2
        ) AS total_stock_sold_percentage,
        IFNULL(sg.average_days_between_sales,0) AS average_days_between_sales,
        IFNULL(vg.total_views,0) AS total_views,
        IFNULL(vg.total_atc,0) AS total_atc
    FROM grouped_items gi
    LEFT JOIN sales_grouped sg 
        ON sg.Item_Name = gi.Item_Name AND sg.Category = gi.Category
    LEFT JOIN views_grouped vg 
        ON vg.Item_Name = gi.Item_Name AND vg.Category = gi.Category
    ORDER BY gi.Item_Name;
    """

    try:
        cursor.execute(query)
        results = cursor.fetchall()
    except mysql.connector.Error as e:
        cursor.close()
        conn.close()
        return {"error": f"MySQL execution failed: {e}"}

    # Add size-level breakdown for each item
    size_cursor = conn.cursor(dictionary=True)
    for row in results:
        item_name = row["item_name"]

        size_query = """
        SELECT 
            i.Size AS size,
            i.Current_Stock AS current_stock,
            (i.Current_Stock + IFNULL(SUM(s.Quantity),0)) AS total_stock,
            IFNULL(SUM(s.Quantity),0) AS total_quantity_sold,
            IFNULL((
                SELECT AVG(diff_days)
                FROM (
                    SELECT DATEDIFF(curr.Date, prev.Date) AS diff_days
                    FROM sale curr
                    JOIN sale prev
                      ON curr.Item_Id = prev.Item_Id
                     AND curr.Date > prev.Date
                     AND curr.Item_Id = i.Item_Id
                ) diffs
            ), 0) AS average_days_between_sales,
            IFNULL((
                SELECT DATEDIFF(CURRENT_DATE, MAX(s2.Date))
                FROM sale s2
                WHERE s2.Item_Id = i.Item_Id
            ), 0) AS days_since_last_sold
        FROM items i
        LEFT JOIN sale s ON s.Item_Id = i.Item_Id
        WHERE i.Item_Name = %s
        GROUP BY i.Item_Id, i.Size, i.Current_Stock;
        """
        size_cursor.execute(size_query, (item_name,))
        size_data = size_cursor.fetchall()

        total_variants = len(size_data)
        variants_in_stock = sum(1 for sd in size_data if int(sd["current_stock"] or 0) > 0)

        sizewise_one_line = [
            {
                "size": sd["size"],
                "current_stock": int(sd["current_stock"] or 0),
                "total_quantity_sold": int(sd["total_quantity_sold"] or 0),
                "average_days_between_sales": float(sd["average_days_between_sales"] or 0),
                "days_since_last_sold": int(sd["days_since_last_sold"] or 0)
            }
            for sd in size_data
        ]

        row["size_summary"] = {
            "size": f"{variants_in_stock}/{total_variants}",
            "sizewise": sizewise_one_line
        }

    size_cursor.close()
    cursor.close()
    conn.close()

    return {
        "status": "✅ Success",
        "database": db_name,
        "launch_start_days": launch_start_days,
        "launch_end_days": launch_end_days,
        "today": str(today),
        "products": results
    }
