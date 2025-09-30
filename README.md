# FastAPI Inventory Analytics API

**Enterprise-ready FastAPI backend for real-time retail product analytics and inventory intelligence using SQLAlchemy and MySQL.**

---

## Overview
This project is a **scalable, high-performance backend API** designed for retail product and inventory analytics. It fetches, aggregates, and exposes detailed product and sales metrics from relational databases, enabling businesses to monitor:  

- Stock levels  
- Sales velocity  
- Customer engagement  
- Projected sell-through  

The API supports both **JSON responses** and **CSV exports**, making it suitable for integration with **dashboards, BI tools, and reporting pipelines**.

---

## Key Features
- **Multi-database support:** Connect dynamically to multiple product databases.  
- **Comprehensive product analytics:** Track stock, sales, views, Add-to-Cart (ATC), days since launch, projected sell-out, and sell-through percentage.  
- **RESTful endpoints:**  
  - `/products` → JSON data for all products  
  - `/products/by_name` → Aggregated metrics by product name or category  
  - `/products/csv` → Download full CSV export  
- **Scalable and modular architecture:** Designed for enterprise usage and easy expansion.  
- **Interactive API documentation:** Auto-generated Swagger UI (`/docs`) for testing and exploration.  
- **Environment-driven configuration:** Use `.env` for secure and flexible database connections.  

---

## Tech Stack
- **Python 3.x**  
- **FastAPI** – high-performance web framework  
- **SQLAlchemy** – ORM for database management  
- **PyMySQL** – MySQL driver  
- **MySQL** – relational database backend  

---

## Project Structure
fastapi-inventory-analytics/
│── main.py # FastAPI entrypoint
│── db.py # Database connection management
│── test_db.py # Database connection test script
│── models/ # Database schema models
│── .env # Environment variables (DB credentials)
│── README.md # Project documentation

---

## Endpoints
- **GET /products** → Retrieve all products filtered by days since launch  
- **GET /products/by_name** → Aggregate metrics by product name or category  
- **GET /products/csv** → Export all product metrics in CSV format  
