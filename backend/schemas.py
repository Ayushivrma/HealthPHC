from pydantic import BaseModel
from typing import Optional


# ==================================================
# PHC SCHEMA
# ==================================================

class PHCCreate(BaseModel):
    name: str
    district: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ==================================================
# MEDICINE SCHEMA
# ==================================================

class MedicineCreate(BaseModel):
    name: str
    category: Optional[str] = None


# ==================================================
# INVENTORY SCHEMAS
# ==================================================

class InventoryCreate(BaseModel):
    phc_id: int
    medicine_id: int
    quantity: int
    minimum_stock: int = 10


class InventoryUpdate(BaseModel):
    quantity: int
    minimum_stock: Optional[int] = None


# ==================================================
# SUPPLIER SCHEMA
# ==================================================

class SupplierCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


# ==================================================
# TRANSFER REQUEST SCHEMA
# ==================================================

class TransferRequestCreate(BaseModel):
    from_phc_id: int
    to_phc_id: int
    medicine_id: int
    quantity: int

class SupplierAlertCreate(BaseModel):
    supplier_id: int
    phc_id: int
    medicine_id: int