"""SQLAlchemy models for khobep_v1 — using shared nhahang_v1 database schema."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class DishCategory(Base):
    """Menu categories — shared table, read-only from khobep."""
    __tablename__ = "dish_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dishes: Mapped[list["Dish"]] = relationship("Dish", back_populates="category")


class Dish(Base):
    """Dishes — shared table, khobep reads subset of columns."""
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 0), nullable=False)
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("dish_categories.id"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped["DishCategory"] = relationship("DishCategory", back_populates="dishes")
    recipes: Mapped[list["Recipe"]] = relationship("Recipe", back_populates="dish")


class Ingredient(Base):
    """Ingredients with inline stock — the core shared table."""
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    stock_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    warning_threshold: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    recipes: Mapped[list["Recipe"]] = relationship("Recipe", back_populates="ingredient")
    import_items: Mapped[list["ImportReceiptItem"]] = relationship("ImportReceiptItem", back_populates="ingredient")


class Recipe(Base):
    """Recipe formulas — shared table, read-only from khobep."""
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dish_id: Mapped[int] = mapped_column(Integer, ForeignKey("dishes.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    dish: Mapped["Dish"] = relationship("Dish", back_populates="recipes")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="recipes")


class ImportReceipt(Base):
    """Import receipt header — khobep-owned table."""
    __tablename__ = "import_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_by: Mapped[str] = mapped_column(String(100), default="Nhan vien kho")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["ImportReceiptItem"]] = relationship("ImportReceiptItem", back_populates="import_receipt", cascade="all, delete-orphan")


class ImportReceiptItem(Base):
    """Import receipt line items — khobep-owned table."""
    __tablename__ = "import_receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_receipt_id: Mapped[int] = mapped_column(Integer, ForeignKey("import_receipts.id", ondelete="CASCADE"))
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    import_receipt: Mapped["ImportReceipt"] = relationship("ImportReceipt", back_populates="items")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="import_items")
