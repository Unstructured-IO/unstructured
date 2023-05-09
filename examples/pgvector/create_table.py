from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    func,
    VECTOR,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create a connection to the PostgreSQL database using the psycopg2 driver
connection_string = "postgresql://localhost:5432/postgres"
engine = create_engine(connection_string)

# Create a declarative base class to define the ORM schema
Base = declarative_base()


ADA_TOKEN_COUNT = 1536


# Define the ORM class for the items table
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    embedding = Column(Vector(ADA_TOKEN_COUNT))
    source = Column(String)
    filename = Column(String)
    page_number = Column(Integer)
    category = Column(String)
    date = Column(DateTime)


# Create the table in the database
Base.metadata.create_all(engine)

# Create a session to interact with the database
Session = sessionmaker(bind=engine)
session = Session()

# Insert data into the items table
session.add_all(
    [
        Item(
            embedding=[1, 2, 3],
            source="../../example-docs/copy-protected.pdf",
            filename="../../example-docs/copy-protected.pdf",
            page_number=2,
            category="NarrativeText",
            date=datetime.datetime(2023, 5, 9, 15, 58, 56, 419472),
        ),
        Item(
            embedding=[4, 5, 6],
            source="../../example-docs/copy-protected.pdf",
            filename="../../example-docs/copy-protected.pdf",
            page_number=2,
            category="NarrativeText",
            date=datetime.datetime(2023, 5, 9, 15, 58, 56, 419472),
        ),
    ]
)
session.commit()

# Query the items table and order the results by the distance between the embedding column and a given vector
query = (
    session.query(Item).order_by(func.cube_distance(Item.embedding, [3, 1, 2])).limit(5)
)

# Iterate over the query results and print them
for item in query:
    print(
        item.id,
        item.embedding,
        item.source,
        item.filename,
        item.page_number,
        item.category,
        item.date,
    )
