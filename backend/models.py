from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from database import Base


# ==================================================
# PHC
# ==================================================

class PHC(Base):
    __tablename__ = "phcs"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    district = Column(String, nullable=False)
    state = Column(String, nullable=False)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)


# ==================================================
# MEDICINE
# ==================================================

class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    category = Column(String, nullable=True)


# ==================================================
# INVENTORY
# ==================================================

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)

    phc_id = Column(
        Integer,
        ForeignKey("phcs.id"),
        nullable=False
    )

    medicine_id = Column(
        Integer,
        ForeignKey("medicines.id"),
        nullable=False
    )

    quantity = Column(Integer, default=0)

    minimum_stock = Column(
        Integer,
        default=10
    )


# ==================================================
# SUPPLIER
# ==================================================

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    phone = Column(String, nullable=True)

    email = Column(String, nullable=True)


# ==================================================
# BED
# ==================================================

class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)

    phc_id = Column(
        Integer,
        ForeignKey("phcs.id"),
        nullable=False
    )

    total_beds = Column(
        Integer,
        default=0
    )

    occupied_beds = Column(
        Integer,
        default=0
    )


# ==================================================
# STAFF
# ==================================================

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)

    phc_id = Column(
        Integer,
        ForeignKey("phcs.id"),
        nullable=False
    )

    name = Column(String, nullable=False)

    role = Column(String, nullable=False)

    present = Column(
        Boolean,
        default=False
    )


# ==================================================
# PATIENT VISITS
# ==================================================

class PatientVisit(Base):
    __tablename__ = "patient_visits"

    id = Column(Integer, primary_key=True, index=True)

    phc_id = Column(
        Integer,
        ForeignKey("phcs.id"),
        nullable=False
    )

    date = Column(
        String,
        nullable=False
    )

    patient_count = Column(
        Integer,
        default=0
    )


# ==================================================
# TRANSFER REQUEST
# ==================================================

class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # PHC which has the medicine
    from_phc_id = Column(
        Integer,
        ForeignKey("phcs.id"),
        nullable=False
    )

    # PHC which needs the medicine
    to_phc_id = Column(
        Integer,
        ForeignKey("phcs.id"),
        nullable=False
    )

    medicine_id = Column(
        Integer,
        ForeignKey("medicines.id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    status = Column(
        String,
        default="PENDING"
    )

    # ==================================================
# SUPPLIER ALERT
# ==================================================

class SupplierAlert(Base):
    __tablename__ = "supplier_alerts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=False
    )

    phc_id = Column(
        Integer,
        ForeignKey("phcs.id"),
        nullable=False
    )

    medicine_id = Column(
        Integer,
        ForeignKey("medicines.id"),
        nullable=False
    )

    message = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        default="PENDING"
    )