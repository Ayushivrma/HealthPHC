from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from forecast_model import forecast_next_days
import models
import schemas
import httpx

from federated_model import (
    train_local_model,
    federated_average
)

import pytesseract
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

from database import engine, get_db


# Create database tables
models.Base.metadata.create_all(bind=engine)



# Create FastAPI application
app = FastAPI(
    title="HealthResQ AI",
    description="AI-powered healthcare resource management platform",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "HealthResQ AI Backend is running!"
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# ==================================================
# PHC APIs
# ==================================================


@app.post("/phcs")
def create_phc(
    phc: schemas.PHCCreate,
    db: Session = Depends(get_db)
):

    new_phc = models.PHC(
        name=phc.name,
        district=phc.district,
        state=phc.state,
        latitude=phc.latitude,
        longitude=phc.longitude
    )

    db.add(new_phc)
    db.commit()
    db.refresh(new_phc)

    return {
        "message": "PHC created successfully",
        "phc_id": new_phc.id,
        "name": new_phc.name
    }


@app.get("/phcs")
def get_phcs(
    db: Session = Depends(get_db)
):

    phcs = db.query(models.PHC).all()

    return phcs


# ==================================================
# MEDICINE APIs
# ==================================================


@app.post("/medicines")
def create_medicine(
    medicine: schemas.MedicineCreate,
    db: Session = Depends(get_db)
):

    new_medicine = models.Medicine(
        name=medicine.name,
        category=medicine.category
    )

    db.add(new_medicine)
    db.commit()
    db.refresh(new_medicine)

    return {
        "message": "Medicine added successfully",
        "medicine_id": new_medicine.id,
        "name": new_medicine.name
    }


@app.get("/medicines")
def get_medicines(
    db: Session = Depends(get_db)
):

    medicines = db.query(models.Medicine).all()

    return medicines

@app.get("/medicines/search")
async def search_medicines(name: str):
    if not name.strip():
        return []

    url = "https://rxnav.nlm.nih.gov/REST/drugs.json"

    params = {
        "name": name
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    groups = data.get("drugGroup", {}).get("conceptGroup", [])

    results = []

    for group in groups:
        concepts = group.get("conceptProperties", [])

        for item in concepts:
            results.append({
                "name": item.get("name"),
                "rxcui": item.get("rxcui")
            })

    return results[:20]


# ==================================================
# INVENTORY APIs
# ==================================================


# ADD INVENTORY
@app.post("/inventory")
def add_inventory(
    inventory: schemas.InventoryCreate,
    db: Session = Depends(get_db)
):

    # Check whether PHC exists
    phc = db.query(models.PHC).filter(
        models.PHC.id == inventory.phc_id
    ).first()

    if not phc:
        raise HTTPException(
            status_code=404,
            detail="PHC not found"
        )


    # Check whether medicine exists
    medicine = db.query(models.Medicine).filter(
        models.Medicine.id == inventory.medicine_id
    ).first()

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )


    # Check if inventory already exists
    existing_inventory = db.query(models.Inventory).filter(
        models.Inventory.phc_id == inventory.phc_id,
        models.Inventory.medicine_id == inventory.medicine_id
    ).first()


    if existing_inventory:

        existing_inventory.quantity = inventory.quantity
        existing_inventory.minimum_stock = inventory.minimum_stock

        db.commit()
        db.refresh(existing_inventory)

        return {
            "message": "Inventory updated successfully",
            "inventory_id": existing_inventory.id,
            "quantity": existing_inventory.quantity
        }


    # Create new inventory
    new_inventory = models.Inventory(
        phc_id=inventory.phc_id,
        medicine_id=inventory.medicine_id,
        quantity=inventory.quantity,
        minimum_stock=inventory.minimum_stock
    )

    db.add(new_inventory)
    db.commit()
    db.refresh(new_inventory)

    return {
        "message": "Inventory added successfully",
        "inventory_id": new_inventory.id,
        "quantity": new_inventory.quantity
    }


# --------------------------------------------------
# GET INVENTORY OF A PHC
# --------------------------------------------------

@app.get("/inventory/{phc_id}")
def get_inventory(
    phc_id: int,
    db: Session = Depends(get_db)
):

    inventory = db.query(models.Inventory).filter(
        models.Inventory.phc_id == phc_id
    ).all()

    result = []

    for item in inventory:

        medicine = db.query(models.Medicine).filter(
            models.Medicine.id == item.medicine_id
        ).first()

        if item.quantity == 0:

            status = "OUT_OF_STOCK"

        elif item.quantity <= item.minimum_stock:

            status = "LOW_STOCK"

        else:

            status = "AVAILABLE"


        result.append({
            "inventory_id": item.id,
            "phc_id": item.phc_id,
            "medicine_id": item.medicine_id,
            "medicine_name": medicine.name if medicine else "Unknown",
            "quantity": item.quantity,
            "minimum_stock": item.minimum_stock,
            "status": status
        })


    return result


# --------------------------------------------------
# UPDATE INVENTORY
# --------------------------------------------------

@app.put("/inventory/{inventory_id}")
def update_inventory(
    inventory_id: int,
    inventory: schemas.InventoryUpdate,
    db: Session = Depends(get_db)
):

    item = db.query(models.Inventory).filter(
        models.Inventory.id == inventory_id
    ).first()


    if not item:

        raise HTTPException(
            status_code=404,
            detail="Inventory item not found"
        )


    if inventory.quantity < 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be negative"
        )


    item.quantity = inventory.quantity


    if inventory.minimum_stock is not None:

        item.minimum_stock = inventory.minimum_stock


    db.commit()
    db.refresh(item)


    if item.quantity == 0:

        status = "OUT_OF_STOCK"

    elif item.quantity <= item.minimum_stock:

        status = "LOW_STOCK"

    else:

        status = "AVAILABLE"


    return {
        "message": "Inventory updated successfully",
        "inventory_id": item.id,
        "quantity": item.quantity,
        "minimum_stock": item.minimum_stock,
        "status": status
    }
@app.delete("/inventory/{inventory_id}")
def delete_inventory(
    inventory_id: int,
    db: Session = Depends(get_db)
):
    item = db.query(models.Inventory).filter(
        models.Inventory.id == inventory_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found"
        )

    db.delete(item)
    db.commit()

    return {
        "message": "Inventory deleted successfully",
        "inventory_id": inventory_id
    }


# --------------------------------------------------
# LOW STOCK INVENTORY
# --------------------------------------------------

@app.get("/inventory/alerts/low-stock")
def low_stock_alerts(
    db: Session = Depends(get_db)
):

    inventory = db.query(models.Inventory).filter(
        models.Inventory.quantity <= models.Inventory.minimum_stock
    ).all()


    result = []


    for item in inventory:

        medicine = db.query(models.Medicine).filter(
            models.Medicine.id == item.medicine_id
        ).first()

        phc = db.query(models.PHC).filter(
            models.PHC.id == item.phc_id
        ).first()


        if item.quantity == 0:

            status = "OUT_OF_STOCK"

        else:

            status = "LOW_STOCK"


        result.append({
            "phc_id": item.phc_id,
            "phc_name": phc.name if phc else "Unknown",
            "medicine_id": item.medicine_id,
            "medicine_name": medicine.name if medicine else "Unknown",
            "quantity": item.quantity,
            "minimum_stock": item.minimum_stock,
            "status": status
        })


    return result

# ==================================================
# PRESCRIPTION UPLOAD
# ==================================================

import os
import shutil


UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/prescription/upload")
async def upload_prescription(
    file: UploadFile = File(...)
):

    # Check file type

    allowed_types = [
        "image/jpeg",
        "image/png",
        "application/pdf"
    ]

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG or PDF files are allowed"
        )


    # Create file path

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )


    # Save uploaded file

    with open(file_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    return {
        "message": "Prescription uploaded successfully",
        "filename": file.filename,
        "file_path": file_path,
        "content_type": file.content_type
    }

# ==================================================
# PRESCRIPTION OCR
# ==================================================

@app.post("/prescription/ocr")
async def prescription_ocr(
    file: UploadFile = File(...)
):

    # Check file type

    allowed_types = [
        "image/jpeg",
        "image/png"
    ]

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG images are allowed"
        )


    # Save temporary file

    temp_path = os.path.join(
        UPLOAD_FOLDER,
        "ocr_temp_" + file.filename
    )


    with open(temp_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    try:

        # Open image

        image = Image.open(temp_path)


        # Perform OCR

        extracted_text = pytesseract.image_to_string(
            image
        )


        return {
            "message": "OCR completed successfully",
            "extracted_text": extracted_text
        }


    finally:

        # Delete temporary file

        if os.path.exists(temp_path):

            os.remove(temp_path)

            # ==================================================
# EXTRACT MEDICINES FROM OCR TEXT
# ==================================================

@app.post("/prescription/extract-medicines")
async def extract_medicines(
    file: UploadFile = File(...)
):

    allowed_types = [
        "image/jpeg",
        "image/png"
    ]

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG images are allowed"
        )


    temp_path = os.path.join(
        UPLOAD_FOLDER,
        "extract_temp_" + file.filename
    )


    with open(temp_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    try:

        image = Image.open(temp_path)

        extracted_text = pytesseract.image_to_string(
            image
        )


        # Get medicines from database

        db = next(get_db())

        medicines = db.query(
            models.Medicine
        ).all()


        found_medicines = []


        text_lower = extracted_text.lower()


        for medicine in medicines:

            if medicine.name.lower() in text_lower:

                found_medicines.append({
                    "medicine_id": medicine.id,
                    "medicine_name": medicine.name,
                    "status": "FOUND"
                })


        return {
            "extracted_text": extracted_text,
            "medicines": found_medicines
        }


    finally:

        if os.path.exists(temp_path):

            os.remove(temp_path)

            # ==================================================
# PRESCRIPTION INVENTORY CHECK
# ==================================================

@app.get("/prescription/check/{phc_id}")
def check_prescription_inventory(
    phc_id: int,
    medicine_ids: str,
    db: Session = Depends(get_db)
):

    # Check whether PHC exists

    phc = db.query(models.PHC).filter(
        models.PHC.id == phc_id
    ).first()

    if not phc:

        raise HTTPException(
            status_code=404,
            detail="PHC not found"
        )


    # Convert medicine IDs from string to list

    try:

        medicine_id_list = [
            int(x.strip())
            for x in medicine_ids.split(",")
        ]

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid medicine IDs"
        )


    result = []


    # Check every medicine

    for medicine_id in medicine_id_list:

        medicine = db.query(models.Medicine).filter(
            models.Medicine.id == medicine_id
        ).first()


        if not medicine:

            result.append({
                "medicine_id": medicine_id,
                "medicine_name": "Unknown",
                "status": "MEDICINE_NOT_FOUND"
            })

            continue


        # Find inventory

        inventory = db.query(models.Inventory).filter(
            models.Inventory.phc_id == phc_id,
            models.Inventory.medicine_id == medicine_id
        ).first()


        # No inventory record

        if not inventory:

            result.append({
                "medicine_id": medicine_id,
                "medicine_name": medicine.name,
                "quantity": 0,
                "minimum_stock": 0,
                "status": "OUT_OF_STOCK"
            })

            continue


        # Determine stock status

        if inventory.quantity == 0:

            status = "OUT_OF_STOCK"

        elif inventory.quantity <= inventory.minimum_stock:

            status = "LOW_STOCK"

        else:

            status = "AVAILABLE"


        result.append({
            "medicine_id": medicine.id,
            "medicine_name": medicine.name,
            "quantity": inventory.quantity,
            "minimum_stock": inventory.minimum_stock,
            "status": status
        })


    return {
        "phc_id": phc.id,
        "phc_name": phc.name,
        "medicines": result
    }

# ==================================================
# NEARBY PHC MEDICINE SEARCH
# ==================================================

@app.get("/nearby-phcs/{phc_id}")
def find_nearby_phcs(
    phc_id: int,
    medicine_id: int,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------
    # Check current PHC
    # --------------------------------------------------

    current_phc = db.query(models.PHC).filter(
        models.PHC.id == phc_id
    ).first()

    if not current_phc:

        raise HTTPException(
            status_code=404,
            detail="PHC not found"
        )


    # --------------------------------------------------
    # Check medicine
    # --------------------------------------------------

    medicine = db.query(models.Medicine).filter(
        models.Medicine.id == medicine_id
    ).first()

    if not medicine:

        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )


    # --------------------------------------------------
    # Find other PHCs in same district
    # --------------------------------------------------

    nearby_phcs = db.query(models.PHC).filter(
        models.PHC.district == current_phc.district,
        models.PHC.id != current_phc.id
    ).all()


    result = []


    # --------------------------------------------------
    # Check medicine stock in each PHC
    # --------------------------------------------------

    for phc in nearby_phcs:

        inventory = db.query(models.Inventory).filter(
            models.Inventory.phc_id == phc.id,
            models.Inventory.medicine_id == medicine_id
        ).first()


        # If medicine exists and stock is available

        if inventory and inventory.quantity > 0:

            result.append({
                "phc_id": phc.id,
                "phc_name": phc.name,
                "district": phc.district,
                "state": phc.state,
                "medicine_id": medicine.id,
                "medicine_name": medicine.name,
                "available_quantity": inventory.quantity,
                "minimum_stock": inventory.minimum_stock,
                "transferable_quantity": max(
                    0,
                    inventory.quantity - inventory.minimum_stock
                ),
                "status": "AVAILABLE_FOR_TRANSFER"
            })


    # --------------------------------------------------
    # Return result
    # --------------------------------------------------

    return {
        "requesting_phc_id": current_phc.id,
        "requesting_phc_name": current_phc.name,
        "medicine_id": medicine.id,
        "medicine_name": medicine.name,
        "nearby_phcs": result
    }

# ==================================================
# SUPPLIER ALERT
# ==================================================

@app.post("/supplier-alert")
def create_supplier_alert(
    alert: schemas.SupplierAlertCreate,
    db: Session = Depends(get_db)
):

    # Check supplier
    supplier = db.query(models.Supplier).filter(
        models.Supplier.id == alert.supplier_id
    ).first()

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )

    # Check PHC
    phc = db.query(models.PHC).filter(
        models.PHC.id == alert.phc_id
    ).first()

    if not phc:
        raise HTTPException(
            status_code=404,
            detail="PHC not found"
        )

    # Check medicine
    medicine = db.query(models.Medicine).filter(
        models.Medicine.id == alert.medicine_id
    ).first()

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # Check inventory
    inventory = db.query(models.Inventory).filter(
        models.Inventory.phc_id == alert.phc_id,
        models.Inventory.medicine_id == alert.medicine_id
    ).first()

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Medicine inventory not found"
        )

    # Create message
    if inventory.quantity == 0:

        message = (
            f"URGENT: {medicine.name} is out of stock "
            f"at {phc.name}. Immediate replenishment required."
        )

    else:

        message = (
            f"LOW STOCK: {medicine.name} stock at "
            f"{phc.name} is {inventory.quantity}. "
            f"Minimum required stock is "
            f"{inventory.minimum_stock}."
        )

    # Create alert
    new_alert = models.SupplierAlert(
        supplier_id=alert.supplier_id,
        phc_id=alert.phc_id,
        medicine_id=alert.medicine_id,
        message=message,
        status="PENDING"
    )

    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    return {
        "message": "Supplier alert created successfully",
        "alert_id": new_alert.id,
        "supplier": supplier.name,
        "phc": phc.name,
        "medicine": medicine.name,
        "stock": inventory.quantity,
        "status": new_alert.status,
        "alert_message": message
    }

# ==================================================
# GET SUPPLIER ALERTS
# ==================================================

@app.get("/supplier-alerts")
def get_supplier_alerts(
    db: Session = Depends(get_db)
):

    alerts = db.query(
        models.SupplierAlert
    ).all()

    result = []

    for alert in alerts:

        supplier = db.query(
            models.Supplier
        ).filter(
            models.Supplier.id == alert.supplier_id
        ).first()

        phc = db.query(
            models.PHC
        ).filter(
            models.PHC.id == alert.phc_id
        ).first()

        medicine = db.query(
            models.Medicine
        ).filter(
            models.Medicine.id == alert.medicine_id
        ).first()

        result.append({
            "alert_id": alert.id,
            "supplier_name": (
                supplier.name
                if supplier
                else "Unknown"
            ),
            "phc_name": (
                phc.name
                if phc
                else "Unknown"
            ),
            "medicine_name": (
                medicine.name
                if medicine
                else "Unknown"
            ),
            "message": alert.message,
            "status": alert.status
        })

    return result

# ==================================================
# CREATE SUPPLIER
# ==================================================

@app.post("/suppliers")
def create_supplier(
    supplier: schemas.SupplierCreate,
    db: Session = Depends(get_db)
):

    new_supplier = models.Supplier(
        name=supplier.name,
        phone=supplier.phone,
        email=supplier.email
    )

    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)

    return {
        "message": "Supplier created successfully",
        "supplier_id": new_supplier.id,
        "name": new_supplier.name
    }

    # ==================================================
# DAY 10 - DEMAND FORECASTING
# ==================================================

@app.get("/demand-forecast/{phc_id}")
def demand_forecast(
    phc_id: int,
    medicine_id: int,
    db: Session = Depends(get_db)
):

    # ----------------------------------------------
    # Check PHC
    # ----------------------------------------------

    phc = db.query(models.PHC).filter(
        models.PHC.id == phc_id
    ).first()

    if not phc:
        raise HTTPException(
            status_code=404,
            detail="PHC not found"
        )

    # ----------------------------------------------
    # Check Medicine
    # ----------------------------------------------

    medicine = db.query(models.Medicine).filter(
        models.Medicine.id == medicine_id
    ).first()

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # ----------------------------------------------
    # Get Inventory
    # ----------------------------------------------

    inventory = db.query(models.Inventory).filter(
        models.Inventory.phc_id == phc_id,
        models.Inventory.medicine_id == medicine_id
    ).first()

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Medicine inventory not found"
        )

    # ----------------------------------------------
    # Get patient visits
    # ----------------------------------------------

    visits = db.query(
        models.PatientVisit
    ).filter(
        models.PatientVisit.phc_id == phc_id
    ).all()

    # ----------------------------------------------
    # Calculate average daily patients
    # ----------------------------------------------

    if len(visits) == 0:

        average_daily_patients = 0

    else:

        total_patients = sum(
            visit.patient_count
            for visit in visits
        )

        average_daily_patients = (
            total_patients / len(visits)
        )

    # ----------------------------------------------
    # Estimate medicine demand
    # ----------------------------------------------
    # Assumption:
    # 1 patient requires approximately 1 unit
    # of the selected medicine.

    average_daily_demand = average_daily_patients

    # ----------------------------------------------
    # Estimate days until stock-out
    # ----------------------------------------------

    if average_daily_demand > 0:

        estimated_days_remaining = (
            inventory.quantity /
            average_daily_demand
        )

    else:

        estimated_days_remaining = None

    # ----------------------------------------------
    # Stock-out warning
    # ----------------------------------------------

    if inventory.quantity == 0:

        warning = "CRITICAL: Medicine is already out of stock"

    elif estimated_days_remaining is not None and estimated_days_remaining <= 3:

        warning = "HIGH RISK: Stock may run out within 3 days"

    elif estimated_days_remaining is not None and estimated_days_remaining <= 7:

        warning = "WARNING: Stock may run out within 7 days"

    else:

        warning = "Stock level is currently sufficient"

    # ----------------------------------------------
    # Return prediction
    # ----------------------------------------------

    return {
        "phc_id": phc.id,
        "phc_name": phc.name,
        "medicine_id": medicine.id,
        "medicine_name": medicine.name,

        "current_stock": inventory.quantity,

        "average_daily_patients": round(
            average_daily_patients,
            2
        ),

        "estimated_daily_demand": round(
            average_daily_demand,
            2
        ),

        "estimated_days_remaining": (
            round(estimated_days_remaining, 2)
            if estimated_days_remaining is not None
            else None
        ),

        "warning": warning
    }

# ==================================================
# ADD PATIENT VISIT
# ==================================================

@app.post("/patient-visits")
def add_patient_visit(
    phc_id: int,
    date: str,
    patient_count: int,
    db: Session = Depends(get_db)
):

    # Check PHC

    phc = db.query(models.PHC).filter(
        models.PHC.id == phc_id
    ).first()

    if not phc:
        raise HTTPException(
            status_code=404,
            detail="PHC not found"
        )

    if patient_count < 0:
        raise HTTPException(
            status_code=400,
            detail="Patient count cannot be negative"
        )

    new_visit = models.PatientVisit(
        phc_id=phc_id,
        date=date,
        patient_count=patient_count
    )

    db.add(new_visit)
    db.commit()
    db.refresh(new_visit)

    return {
        "message": "Patient visit added successfully",
        "visit_id": new_visit.id,
        "phc_id": phc_id,
        "date": date,
        "patient_count": patient_count
    }

@app.get("/ml-demand-forecast/{phc_id}")
def ml_demand_forecast(
    phc_id: int,
    medicine_id: int,
    db: Session = Depends(get_db)
):

    # Check PHC
    phc = db.query(models.PHC).filter(
        models.PHC.id == phc_id
    ).first()

    if not phc:
        raise HTTPException(
            status_code=404,
            detail="PHC not found"
        )

    # Check medicine
    medicine = db.query(models.Medicine).filter(
        models.Medicine.id == medicine_id
    ).first()

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # Get inventory
    inventory = db.query(models.Inventory).filter(
        models.Inventory.phc_id == phc_id,
        models.Inventory.medicine_id == medicine_id
    ).first()

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Medicine inventory not found"
        )

    # Get patient history
    visits = db.query(models.PatientVisit).filter(
        models.PatientVisit.phc_id == phc_id
    ).order_by(
        models.PatientVisit.id
    ).all()

    patient_counts = [
        visit.patient_count
        for visit in visits
    ]

    # Need at least 2 days of data
    if len(patient_counts) < 2:
        return {
            "message": "At least 2 days of patient data required"
        }

    # ML prediction
    predictions = forecast_next_days(
        patient_counts,
        days=7
    )

    # Average predicted demand
    average_predicted_demand = (
        sum(predictions) / len(predictions)
    )

    # Estimate stock duration
    if average_predicted_demand > 0:

        estimated_days_remaining = (
            inventory.quantity /
            average_predicted_demand
        )

    else:
        estimated_days_remaining = None

    # Warning
    if inventory.quantity == 0:

        warning = "CRITICAL: Medicine is out of stock"

    elif (
        estimated_days_remaining is not None
        and estimated_days_remaining <= 3
    ):

        warning = "HIGH RISK: Stock may run out within 3 days"

    elif (
        estimated_days_remaining is not None
        and estimated_days_remaining <= 7
    ):

        warning = "WARNING: Stock may run out within 7 days"

    else:

        warning = "Stock level is currently sufficient"

    return {

        "phc_id": phc.id,

        "phc_name": phc.name,

        "medicine_id": medicine.id,

        "medicine_name": medicine.name,

        "current_stock": inventory.quantity,

        "historical_patient_data": patient_counts,

        "predicted_next_7_days": predictions,

        "average_predicted_daily_demand": round(
            average_predicted_demand,
            2
        ),

        "estimated_days_remaining": (
            round(
                estimated_days_remaining,
                2
            )
            if estimated_days_remaining is not None
            else None
        ),

        "warning": warning
    }

@app.get("/federated-training")
def federated_training(
    db: Session = Depends(get_db)
):

    phcs = db.query(models.PHC).all()

    local_models = []

    phc_results = []

    for phc in phcs:

        visits = db.query(
            models.PatientVisit
        ).filter(
            models.PatientVisit.phc_id == phc.id
        ).order_by(
            models.PatientVisit.id
        ).all()

        patient_counts = [
            visit.patient_count
            for visit in visits
        ]

        local_model = train_local_model(
            patient_counts
        )

        if local_model is None:
            continue

        local_models.append(
            local_model
        )

        phc_results.append({

            "phc_id": phc.id,

            "phc_name": phc.name,

            "local_data_points":
                len(patient_counts),

            "local_model": local_model
        })

    global_model = federated_average(
        local_models
    )

    if global_model is None:

        return {
            "message":
                "Not enough data for federated training"
        }

    return {

        "message":
            "Federated training completed",

        "privacy_note":
            "Only model parameters were aggregated. "
            "Raw patient data remained at PHC level.",

        "participating_phcs":
            phc_results,

        "global_model":
            global_model
    }

@app.get("/national-dashboard")
def national_dashboard(
    db: Session = Depends(get_db)
):

    phcs = db.query(models.PHC).all()

    total_phcs = len(phcs)

    total_medicines = db.query(
        models.Medicine
    ).count()

    total_stock = db.query(
        models.Inventory
    ).with_entities(
        models.Inventory.quantity
    ).all()

    total_stock_quantity = sum(
        item[0]
        for item in total_stock
    )

    out_of_stock = db.query(
        models.Inventory
    ).filter(
        models.Inventory.quantity == 0
    ).count()

    low_stock = db.query(
        models.Inventory
    ).filter(
        models.Inventory.quantity > 0,
        models.Inventory.quantity <=
        models.Inventory.minimum_stock
    ).count()

    pending_transfers = db.query(
        models.TransferRequest
    ).filter(
        models.TransferRequest.status == "PENDING"
    ).count()

    pending_supplier_alerts = db.query(
        models.SupplierAlert
    ).filter(
        models.SupplierAlert.status == "PENDING"
    ).count()

    total_patients = db.query(
        models.PatientVisit
    ).with_entities(
        models.PatientVisit.patient_count
    ).all()

    total_patient_visits = sum(
        visit[0]
        for visit in total_patients
    )

    return {

        "network_summary": {

            "total_phcs":
                total_phcs,

            "total_medicines":
                total_medicines,

            "total_stock_units":
                total_stock_quantity,

            "total_patient_visits":
                total_patient_visits
        },

        "medicine_status": {

            "out_of_stock":
                out_of_stock,

            "low_stock":
                low_stock
        },

        "operations": {

            "pending_transfers":
                pending_transfers,

            "pending_supplier_alerts":
                pending_supplier_alerts
        }
    }

@app.get("/transfer-requests")
def get_transfer_requests(
    db: Session = Depends(get_db)
):

    requests = db.query(
        models.TransferRequest
    ).all()

    result = []

    for request in requests:

        from_phc = db.query(
            models.PHC
        ).filter(
            models.PHC.id == request.from_phc_id
        ).first()

        to_phc = db.query(
            models.PHC
        ).filter(
            models.PHC.id == request.to_phc_id
        ).first()

        medicine = db.query(
            models.Medicine
        ).filter(
            models.Medicine.id == request.medicine_id
        ).first()

        result.append({

            "request_id": request.id,

            "from_phc": (
                from_phc.name
                if from_phc
                else "Unknown"
            ),

            "to_phc": (
                to_phc.name
                if to_phc
                else "Unknown"
            ),

            "medicine": (
                medicine.name
                if medicine
                else "Unknown"
            ),

            "quantity": request.quantity,

            "status": request.status
        })

    return result

@app.post("/transfer/approve/{request_id}")
def approve_transfer(
    request_id: int,
    db: Session = Depends(get_db)
):

    transfer = db.query(
        models.TransferRequest
    ).filter(
        models.TransferRequest.id == request_id
    ).first()

    if not transfer:

        raise HTTPException(
            status_code=404,
            detail="Transfer request not found"
        )

    if transfer.status != "PENDING":

        raise HTTPException(
            status_code=400,
            detail="Transfer request already processed"
        )

    donor_inventory = db.query(
        models.Inventory
    ).filter(
        models.Inventory.phc_id ==
        transfer.from_phc_id,

        models.Inventory.medicine_id ==
        transfer.medicine_id
    ).first()

    receiver_inventory = db.query(
        models.Inventory
    ).filter(
        models.Inventory.phc_id ==
        transfer.to_phc_id,

        models.Inventory.medicine_id ==
        transfer.medicine_id
    ).first()

    if not donor_inventory:

        raise HTTPException(
            status_code=404,
            detail="Donor inventory not found"
        )

    transferable_quantity = (
        donor_inventory.quantity
        - donor_inventory.minimum_stock
    )

    if transfer.quantity > transferable_quantity:

        raise HTTPException(
            status_code=400,
            detail="Insufficient transferable stock"
        )

    # Remove medicine from donor
    donor_inventory.quantity -= (
        transfer.quantity
    )

    # Add medicine to receiver
    if receiver_inventory:

        receiver_inventory.quantity += (
            transfer.quantity
        )

    else:

        receiver_inventory = models.Inventory(

            phc_id=transfer.to_phc_id,

            medicine_id=transfer.medicine_id,

            quantity=transfer.quantity,

            minimum_stock=10
        )

        db.add(receiver_inventory)

    # Update request status
    transfer.status = "APPROVED"

    db.commit()

    return {

        "message":
            "Transfer approved successfully",

        "request_id":
            transfer.id,

        "transferred_quantity":
            transfer.quantity,

        "status":
            transfer.status
    }
@app.post("/transfer/reject/{request_id}")
def reject_transfer(
    request_id: int,
    db: Session = Depends(get_db)
):

    transfer = db.query(
        models.TransferRequest
    ).filter(
        models.TransferRequest.id == request_id
    ).first()

    if not transfer:

        raise HTTPException(
            status_code=404,
            detail="Transfer request not found"
        )

    if transfer.status != "PENDING":

        raise HTTPException(
            status_code=400,
            detail="Transfer request already processed"
        )

    transfer.status = "REJECTED"

    db.commit()

    return {

        "message":
            "Transfer request rejected",

        "request_id":
            transfer.id,

        "status":
            transfer.status
    }

@app.post("/auto-supplier-alert/{phc_id}/{medicine_id}")
def auto_supplier_alert(
    phc_id: int,
    medicine_id: int,
    supplier_id: int,
    db: Session = Depends(get_db)
):

    phc = db.query(
        models.PHC
    ).filter(
        models.PHC.id == phc_id
    ).first()

    medicine = db.query(
        models.Medicine
    ).filter(
        models.Medicine.id == medicine_id
    ).first()

    supplier = db.query(
        models.Supplier
    ).filter(
        models.Supplier.id == supplier_id
    ).first()

    inventory = db.query(
        models.Inventory
    ).filter(
        models.Inventory.phc_id == phc_id,
        models.Inventory.medicine_id == medicine_id
    ).first()

    if not phc:
        raise HTTPException(
            status_code=404,
            detail="PHC not found"
        )

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found"
        )

    if inventory.quantity == 0:

        message = (
            f"URGENT: {medicine.name} is out of stock "
            f"at {phc.name}. Immediate replenishment required."
        )

    elif inventory.quantity <= inventory.minimum_stock:

        message = (
            f"LOW STOCK: {medicine.name} has only "
            f"{inventory.quantity} units remaining "
            f"at {phc.name}."
        )

    else:

        return {
            "message":
                "Stock level is currently sufficient"
        }

    alert = models.SupplierAlert(

        supplier_id=supplier_id,

        phc_id=phc_id,

        medicine_id=medicine_id,

        message=message,

        status="PENDING"
    )

    db.add(alert)

    db.commit()

    db.refresh(alert)

    return {

        "message":
            "Supplier alert generated automatically",

        "alert_id":
            alert.id,

        "supplier":
            supplier.name,

        "medicine":
            medicine.name,

        "phc":
            phc.name,

        "alert":
            message,

        "status":
            alert.status
    }

@app.get("/system-status")
def system_status(
    db: Session = Depends(get_db)
):

    return {

        "system":
            "HealthResQ AI",

        "status":
            "OPERATIONAL",

        "phcs":
            db.query(models.PHC).count(),

        "medicines":
            db.query(models.Medicine).count(),

        "inventory_records":
            db.query(models.Inventory).count(),

        "transfer_requests":
            db.query(
                models.TransferRequest
            ).count(),

        "supplier_alerts":
            db.query(
                models.SupplierAlert
            ).count(),

        "patient_visit_records":
            db.query(
                models.PatientVisit
            ).count(),

        "modules": [

            "Inventory Management",

            "Prescription OCR",

            "Medicine Availability",

            "Nearby PHC Redistribution",

            "Emergency Transfer",

            "Supplier Alerts",

            "Demand Forecasting",

            "Federated AI",

            "National Dashboard"
        ]
    }