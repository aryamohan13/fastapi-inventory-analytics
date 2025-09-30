from db import get_engine
from sqlalchemy import text

db_name = "zing"

try:
    engine = get_engine(db_name)
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES;"))
        tables = result.fetchall()
        print(f"Connected to '{db_name}'. Tables:")
        for table in tables:
            print(table[0])
except Exception as e:
    print(f"Failed to connect to {db_name}: {e}")