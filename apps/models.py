from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field,  SQLModel, create_engine,  Relationship


class Category(SQLModel, table=True):
    __tablename__ = 'categories'
    id: int | None = Field(default=None, primary_key=True)
    title: str
    products: list['Product'] = Relationship(back_populates="category", passive_deletes="all")


class Product(SQLModel, table=True):
    __tablename__ = 'products'
    id: int | None = Field(default=None, primary_key=True)
    title: str
    photo: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(max_digits=12, decimal_places=2)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category_id: int = Field(foreign_key='categories.id', ondelete='CASCADE')
    category: 'Category' = Relationship(back_populates="products")


class User(SQLModel, table=True):
    __tablename__ = 'users'
    id: int | None = Field(default=None, primary_key=True)
    name: str
    age: int
    username: str = Field(unique=True, index=True)
    password: str

url = 'postgresql://postgres:1@localhost:5433/postgres'
engine = create_engine(url)
SQLModel.metadata.create_all(engine)
