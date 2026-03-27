from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class DishCategory(Base):
    __tablename__ = "dish_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)
    icon = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dishes = relationship("Dish", back_populates="category")


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 0), nullable=False)
    image = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("dish_categories.id"), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("DishCategory", back_populates="dishes")
    recipes = relationship("Recipe", back_populates="dish")
    order_items = relationship("OrderItem", back_populates="dish")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    unit = Column(String(50), nullable=False)
    stock_quantity = Column(Numeric(10, 3), default=0)
    warning_threshold = Column(Numeric(10, 3), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recipes = relationship("Recipe", back_populates="ingredient")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    required_quantity = Column(Numeric(10, 3), nullable=False)

    __table_args__ = (UniqueConstraint("dish_id", "ingredient_id", name="uq_dish_ingredient"),)

    dish = relationship("Dish", back_populates="recipes")
    ingredient = relationship("Ingredient", back_populates="recipes")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(String(50), nullable=True)
    status = Column(
        Enum("pending", "confirmed", "cancelled"), default="pending"
    )
    total_amount = Column(Numeric(10, 0), default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 0), nullable=False)

    order = relationship("Order", back_populates="items")
    dish = relationship("Dish", back_populates="order_items")
