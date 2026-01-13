from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

# Worker schemas
class WorkerBase(BaseModel):
    worker_code: str
    name: str
    contact: Optional[str] = None
    notes: Optional[str] = None

class WorkerCreate(WorkerBase):
    pass

class WorkerUpdate(WorkerBase):
    pass

class WorkerResponse(WorkerBase):
    id: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Settings schemas
class SettingsVersionBase(BaseModel):
    name: str
    rules_json: str
    notes: Optional[str] = None

class SettingsVersionCreate(SettingsVersionBase):
    pass

class SettingsVersionResponse(SettingsVersionBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Job schemas
class JobBase(BaseModel):
    job_code: str
    title: str
    client_name: Optional[str] = None
    job_post_url: str
    upwork_job_id: Optional[str] = None
    upwork_contract_id: Optional[str] = None
    upwork_offer_id: Optional[str] = None
    job_type: str
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    connects_used: Optional[int] = None

class JobCreate(JobBase):
    connect_override_mode: Optional[str] = None
    connect_override_value: Optional[Decimal] = None
    platform_fee_override_enabled: Optional[bool] = None
    platform_fee_override_mode: Optional[str] = None
    platform_fee_override_value: Optional[Decimal] = None
    platform_fee_override_apply_on: Optional[str] = None

class JobUpdate(JobCreate):
    pass

class JobResponse(JobBase):
    id: int
    settings_version_id: int
    is_finalized: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Receipt schemas
class ReceiptBase(BaseModel):
    received_date: date
    amount_received: Decimal
    source: str
    upwork_transaction_id: Optional[str] = None
    notes: Optional[str] = None

class ReceiptCreate(ReceiptBase):
    pass

class ReceiptResponse(ReceiptBase):
    id: int
    job_id: int

    class Config:
        from_attributes = True

# Allocation schemas
class AllocationBase(BaseModel):
    worker_id: Optional[int] = None
    label: str
    role: Optional[str] = None
    share_type: str
    share_value: Decimal
    notes: Optional[str] = None

class AllocationCreate(AllocationBase):
    pass

class AllocationUpdate(AllocationBase):
    pass

class AllocationResponse(AllocationBase):
    id: int
    job_id: int

    class Config:
        from_attributes = True

# Payment schemas
class PaymentBase(BaseModel):
    payment_code: str
    worker_id: int
    job_id: Optional[int] = None
    amount_paid: Decimal
    paid_date: date
    method: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class PaymentResponse(PaymentBase):
    id: int

    class Config:
        from_attributes = True
