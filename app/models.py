from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, Date, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, date
from decimal import Decimal
import enum
from app.database import Base

class JobType(str, enum.Enum):
    FIXED = "fixed"
    HOURLY = "hourly"

class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class ReceiptSource(str, enum.Enum):
    MILESTONE = "milestone"
    WEEKLY = "weekly"
    BONUS = "bonus"
    MANUAL = "manual"

class ShareType(str, enum.Enum):
    PERCENT = "percent"
    FIXED_AMOUNT = "fixed_amount"

class ConnectMode(str, enum.Enum):
    FIXED = "fixed"
    PERCENT = "percent"

class PlatformFeeApplyOn(str, enum.Enum):
    GROSS = "gross"
    NET = "net"

class JobSource(str, enum.Enum):
    UPWORK = "upwork"
    FREELANCER = "freelancer"
    LINKEDIN = "linkedin"
    FIVERR = "fiverr"
    DIRECT = "direct"
    OTHER = "other"

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    worker_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    contact = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    allocations = relationship("JobAllocation", back_populates="worker")
    payments = relationship("Payment", back_populates="worker")

class SettingsVersion(Base):
    __tablename__ = "settings_versions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    rules_json = Column(Text, nullable=False)  # JSON string
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("Job", back_populates="settings_version")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    client_name = Column(String, nullable=True)
    job_post_url = Column(String, nullable=False)
    
    # Job source and description
    source = Column(SQLEnum(JobSource), nullable=True)
    description = Column(Text, nullable=True)  # HTML content from Quill.js
    cover_letter = Column(Text, nullable=True)  # HTML content from Quill.js
    
    # Company/Client details
    company_name = Column(String, nullable=True)
    company_website = Column(String, nullable=True)
    company_email = Column(String, nullable=True)
    company_phone = Column(String, nullable=True)
    company_address = Column(Text, nullable=True)
    client_notes = Column(Text, nullable=True)
    
    # Upwork-specific fields (kept for backward compatibility)
    upwork_job_id = Column(String, nullable=True)
    upwork_contract_id = Column(String, nullable=True)
    upwork_offer_id = Column(String, nullable=True)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.DRAFT)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    # Versioning
    settings_version_id = Column(Integer, ForeignKey("settings_versions.id"), nullable=False)
    
    # Overrides
    connect_override_mode = Column(String, nullable=True)  # fixed_amount/percent_of_received (deprecated)
    connect_override_value = Column(Numeric(10, 2), nullable=True)  # deprecated
    connects_used = Column(Integer, nullable=True)  # Number of connects used for this job
    platform_fee_override_enabled = Column(Boolean, nullable=True)
    platform_fee_override_mode = Column(String, nullable=True)
    platform_fee_override_value = Column(Numeric(10, 2), nullable=True)
    platform_fee_override_apply_on = Column(String, nullable=True)  # gross/net
    
    # Flags
    is_finalized = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    settings_version = relationship("SettingsVersion", back_populates="jobs")
    receipts = relationship("Receipt", back_populates="job", cascade="all, delete-orphan")
    allocations = relationship("JobAllocation", back_populates="job", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="job")
    snapshot = relationship("JobCalculationSnapshot", back_populates="job", uselist=False, cascade="all, delete-orphan")

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    received_date = Column(Date, nullable=False)
    amount_received = Column(Numeric(10, 2), nullable=False)
    source = Column(SQLEnum(ReceiptSource), nullable=False)
    upwork_transaction_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    selected_allocation_ids = Column(Text, nullable=True)  # JSON string of allocation IDs

    job = relationship("Job", back_populates="receipts")

class JobAllocation(Base):
    __tablename__ = "job_allocations"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)  # null = admin/you
    label = Column(String, nullable=False)  # "YOU" or role like Dev/Design
    role = Column(String, nullable=True)
    share_type = Column(SQLEnum(ShareType), nullable=False)
    share_value = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)

    job = relationship("Job", back_populates="allocations")
    worker = relationship("Worker", back_populates="allocations")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_code = Column(String, unique=True, index=True, nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    amount_paid = Column(Numeric(10, 2), nullable=False)
    paid_date = Column(Date, nullable=False)
    method = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_auto_generated = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=False)

    worker = relationship("Worker", back_populates="payments")
    job = relationship("Job", back_populates="payments")

class JobCalculationSnapshot(Base):
    __tablename__ = "job_calculation_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), unique=True, nullable=False)
    settings_version_id = Column(Integer, ForeignKey("settings_versions.id"), nullable=False)
    snapshot_json = Column(Text, nullable=False)  # JSON string
    finalized_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="snapshot")
