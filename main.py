from fastapi import FastAPI, HTTPException # type: ignore
from pydantic import BaseModel, Field, validator # type: ignore
from typing import List, Dict, Optional, Union
from enum import Enum
from abc import ABC, abstractmethod
from fastapi.middleware.cors import CORSMiddleware # type: ignore
import uuid

app = FastAPI(title="Discount Calculation API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    
    @validator("price")
    def validate_price(cls, price):
        if price <= 0:
            raise ValueError("Price must be greater than zero")
        return price

# In-memory database (replace with a real DB in production)
products_db: Dict[str, Product] = {}

# Discount Strategy Pattern
class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FLAT = "flat"
    BOGO = "bogo"

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, product: Product, quantity: int, params: Dict) -> float:
        pass

class PercentageDiscount(DiscountStrategy):
    def calculate(self, product: Product, quantity: int, params: Dict) -> float:
        percentage = params.get("value", 0)
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage discount must be between 0 and 100")
        
        total_price = product.price * quantity
        discount_amount = total_price * (percentage / 100)
        return total_price - discount_amount

class FlatDiscount(DiscountStrategy):
    def calculate(self, product: Product, quantity: int, params: Dict) -> float:
        discount_amount = params.get("value", 0)
        total_price = product.price * quantity
        
        if discount_amount > total_price:
            return 0  # Don't allow negative prices
        
        return total_price - discount_amount

class BOGODiscount(DiscountStrategy):
    def calculate(self, product: Product, quantity: int, params: Dict) -> float:
        if quantity < 2:
            return product.price * quantity  # No discount for single item
        
        # Calculate how many free items should be applied
        free_items = quantity // 2
        paid_items = quantity - free_items
        
        return product.price * paid_items

# Discount factory
discount_strategies = {
    DiscountType.PERCENTAGE: PercentageDiscount(),
    DiscountType.FLAT: FlatDiscount(),
    DiscountType.BOGO: BOGODiscount(),
}

# Request/Response models
class ProductCreate(BaseModel):
    name: str
    price: float

class DiscountRequest(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)
    discounts: List[Dict[str, Union[str, float]]]  # Allow multiple discounts

class DiscountResponse(BaseModel):
    product: Product
    quantity: int
    original_price: float
    discounted_price: float
    savings: float
    applied_discounts: List[Dict]

# API Endpoints
@app.post("/products/", response_model=Product)
async def create_product(product: ProductCreate):
    new_product = Product(name=product.name, price=product.price)
    products_db[new_product.id] = new_product
    return new_product

@app.get("/products/", response_model=List[Product])
async def get_products():
    return list(products_db.values())

@app.post("/calculate-discount/", response_model=DiscountResponse)
async def calculate_discount(request: DiscountRequest):
    # Verify product exists
    if request.product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = products_db[request.product_id]
    original_price = product.price * request.quantity
    current_price = original_price
    applied_discounts = []
    
    # Apply each discount sequentially
    for discount_info in request.discounts:
        discount_type = discount_info.get("type")
        
        if discount_type not in discount_strategies:
            raise HTTPException(status_code=400, detail=f"Invalid discount type: {discount_type}")
        
        try:
            # Calculate this discount based on current price
            strategy = discount_strategies[discount_type]
            new_price = strategy.calculate(product, request.quantity, discount_info)
            
            # Track which discounts were applied and their effect
            applied_discounts.append({
                "type": discount_type,
                "params": discount_info,
                "saved": current_price - new_price
            })
            
            current_price = new_price
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    return DiscountResponse(
        product=product,
        quantity=request.quantity,
        original_price=original_price,
        discounted_price=current_price,
        savings=original_price - current_price,
        applied_discounts=applied_discounts
    )
