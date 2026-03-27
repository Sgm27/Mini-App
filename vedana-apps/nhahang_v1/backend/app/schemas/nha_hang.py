from typing import List, Optional

from pydantic import BaseModel


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: int
    name: str
    sort_order: int
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Dish ──────────────────────────────────────────────────────────────────────

class DishOut(BaseModel):
    id: int
    name: str
    price: float
    image: Optional[str] = None
    description: Optional[str] = None
    category_id: int
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    active: bool
    can_serve: bool = True
    missing_ingredients: List[str] = []

    model_config = {"from_attributes": True}


# ── Availability check ────────────────────────────────────────────────────────

class CartItem(BaseModel):
    dish_id: int
    quantity: int


class DishAvailability(BaseModel):
    dish_id: int
    can_serve: bool
    missing_ingredients: List[str] = []


class MissingIngredient(BaseModel):
    id: int
    name: str
    unit: str
    in_stock: float
    needed: float


class CheckAvailabilityRequest(BaseModel):
    items: List[CartItem]


class CheckAvailabilityResponse(BaseModel):
    can_serve_all: bool
    missing_ingredients: List[MissingIngredient] = []
    dishes: List[DishAvailability] = []


# ── Ingredient / Inventory ────────────────────────────────────────────────────

class IngredientOut(BaseModel):
    id: int
    name: str
    unit: str
    stock_quantity: float
    warning_threshold: float
    low_stock_warning: bool = False

    model_config = {"from_attributes": True}


class IngredientUpdate(BaseModel):
    stock_quantity: float
    warning_threshold: Optional[float] = None


class IngredientCreate(BaseModel):
    name: str
    unit: str
    stock_quantity: float = 0
    warning_threshold: float = 0


# ── Order ─────────────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    table_number: Optional[str] = None
    items: List[CartItem]
    notes: Optional[str] = None


class OrderItemOut(BaseModel):
    dish_id: int
    name: str
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    table_number: Optional[str] = None
    status: str
    total_amount: float
    notes: Optional[str] = None
    items: List[OrderItemOut] = []
    created_at: str

    model_config = {"from_attributes": True}
