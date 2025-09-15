from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    Item_Id = Column(Integer, primary_key=True)
    Item_Name = Column(String(255))
    Item_Type = Column(String(255))
    Item_Code = Column(String(255))
    Sale_Price = Column(Float)
    Sale_Discount = Column(Float)
    Uom = Column(String(255))
    Current_Stock = Column(Integer)
    Is_Public = Column(String(255))
    Category = Column(String(255))
    Colour = Column(String(255))
    Fabric = Column(String(255))
    Fit = Column(String(255))
    Neck = Column(String(255))
    Occasion = Column(String(255))
    Offer = Column(String(255))
    Print = Column(String(255))
    Size = Column(String(255))
    Sleeve = Column(String(255))

    # Double underscore columns → mapped with safe Python names
    batch = Column("__Batch", String(255))
    collection_you_will_love = Column("__Collection_You_Will_Love", String(255))
    details = Column("__Details", String(255))
    eorder = Column("__Eorder__", String(255))
    launch_date = Column("__Launch_Date", Date)   # <-- Fixed
    mood = Column("__Mood", String(255))
    new_item_type = Column("__New_Item_Type", String(255))
    new_launch = Column("__New_Launch", String(255))
    offer_date = Column("__Offer_Date", Date)
    office_wear_collection = Column("__Office_Wear_Collection", String(255))
    price = Column("__Price", Float)
    print_type = Column("__Print_Type", String(255))
    quadrant = Column("__Quadrant", String(255))
    restock_date = Column("__Restock_Date", Date)
    style_type = Column("__Style_Type", String(255))
    feeding_friendly_flag = Column("__Feeding_Friendly", String(255))

    Updated_At = Column(String(255))
    Feeding_Friendly = Column(String(255))
    Launch_Date = Column(String(255))
    Sale_Discount_Rate = Column(Float)
    Sale_Discount_Price = Column(Float)
    Sale_Discount_Mode = Column(String(255))


class Sale(Base):
    __tablename__ = "sale"

    Sale_Id = Column(Integer, primary_key=True)
    Item_Id = Column(Integer, ForeignKey("items.Item_Id"))
    Item_Name = Column(String(255))
    Quantity = Column(Integer)
    Date = Column(Date)


class ViewsAtc(Base):
    __tablename__ = "viewsatc"

    View_Id = Column(Integer, primary_key=True)
    Item_Id = Column(Integer, ForeignKey("items.Item_Id"))
    Items_Viewed = Column(Integer)
    Items_Addedtocart = Column(Integer)
