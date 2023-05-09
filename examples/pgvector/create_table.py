import datetime
import os

from sqlalchemy import (
    create_engine,
    ARRAY,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    func,
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from langchain.embeddings.openai import OpenAIEmbeddings

from unstructured.partition.email import partition_email

EXAMPLE_DOCS_DIRECTORY = "../../example-docs"

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
    text = Column(String)
    filename = Column(String)
    category = Column(String)
    date = Column(DateTime)
    sent_to = Column(ARRAY(String))
    sent_from = Column(ARRAY(String))
    subject = Column(String)


# Create the table in the database
Base.metadata.create_all(engine)

# Create a session to interact with the database
Session = sessionmaker(bind=engine)
session = Session()


elements = []
for f in os.listdir(EXAMPLE_DOCS_DIRECTORY):
    if not f.endswith(".eml"):
        continue

    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, f)
    elements.extend(partition_email(filename=filename))

for element in elements:
    date = element.metadata.date
    if not isinstance(date, str):
        continue

    element.metadata.date = datetime.datetime.fromisoformat(date)

embedding_function = OpenAIEmbeddings()
embeddings = embedding_function.embed_documents([el.text for el in elements])

for i, element in enumerate(elements):
    element.embedding = embeddings[i]

items_to_add = []
for element in elements:
    items_to_add.append(
        Item(
            text=element.text,
            embedding=element.embedding,
            filename=element.metadata.filename,
            date=element.metadata.date,
            sent_to=element.metadata.sent_to,
            sent_from=element.metadata.sent_from,
            subject=element.metadata.subject,
        )
    )


session.add_all(items_to_add)
session.commit()


query = session.query(Item).order_by(Item.embedding.l2_distance(vector)).limit(5)
for item in query:
    print(item.id, item.text)

# Query the items table and order the results by the distance between the embedding column and a given vector
# query = (
#     session.query(Item).order_by(func.cube_distance(Item.embedding, [3, 1, 2])).limit(5)
# )
#
# # Iterate over the query results and print them
# for item in query:
#     print(
#         item.id,
#         item.embedding,
#         item.filename,
#         item.page_number,
#         item.category,
#         item.date,
#     )
