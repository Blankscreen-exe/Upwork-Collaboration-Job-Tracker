from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional
import json
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models import Job, Receipt, JobAllocation, Payment, SettingsVersion, Worker

def quantize_decimal(value: Decimal, places: int = 2) -> Decimal:
    """Round decimal to specified places"""
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def get_settings_rules(settings_version: SettingsVersion) -> Dict[str, Any]:
    """Parse and return settings rules from JSON"""
    return json.loads(settings_version.rules_json)

def get_job_totals(job: Job, receipts: List[Receipt], settings_version: SettingsVersion) -> Dict[str, Any]:
    """Calculate job totals: received, connect deduction, platform fee, net distributable"""
    rules = get_settings_rules(settings_version)
    
    # Total received
    total_received = sum((Decimal(str(r.amount_received)) for r in receipts), Decimal(0))
    
    # Connect deduction - based on connects used
    connects_used = job.connects_used or 0
    connect_cost_per_unit = Decimal(str(rules.get("connect_cost_per_unit", 0)))
    connect_deduction = Decimal(connects_used) * connect_cost_per_unit
    connect_deduction = quantize_decimal(connect_deduction)
    
    # Platform fee
    platform_fee_enabled = job.platform_fee_override_enabled
    if platform_fee_enabled is None:
        platform_fee_enabled = rules.get("platform_fee", {}).get("enabled", False)
    
    platform_fee = Decimal(0)
    if platform_fee_enabled:
        platform_fee_mode = job.platform_fee_override_mode or rules.get("platform_fee", {}).get("mode", "percent")
        platform_fee_value = job.platform_fee_override_value or Decimal(str(rules.get("platform_fee", {}).get("value", 0)))
        platform_fee_apply_on = job.platform_fee_override_apply_on or rules.get("platform_fee", {}).get("apply_on", "net")
        
        if platform_fee_apply_on == "gross":
            base_amount = total_received
        else:  # net
            base_amount = total_received - connect_deduction
        
        if platform_fee_mode == "percent":
            platform_fee = base_amount * platform_fee_value
        else:  # fixed
            platform_fee = platform_fee_value
        
        platform_fee = quantize_decimal(platform_fee)
    
    # Net distributable
    net_distributable = total_received - connect_deduction - platform_fee
    net_distributable = quantize_decimal(net_distributable)
    
    return {
        "total_received": total_received,
        "connect_deduction": connect_deduction,
        "platform_fee": platform_fee,
        "net_distributable": net_distributable
    }

def compute_allocations(
    job: Job,
    allocations: List[JobAllocation],
    totals: Dict[str, Any],
    settings_version: SettingsVersion
) -> List[Dict[str, Any]]:
    """Compute earned amounts for each allocation"""
    rules = get_settings_rules(settings_version)
    net_distributable = totals["net_distributable"]
    
    results = []
    for alloc in allocations:
        if alloc.share_type == "percent":
            earned = net_distributable * Decimal(str(alloc.share_value))
        else:  # fixed_amount
            earned = Decimal(str(alloc.share_value))
        
        earned = quantize_decimal(earned)
        
        results.append({
            "allocation": alloc,
            "earned": earned
        })
    
    return results

def compute_worker_totals(worker_id: int, db: Session) -> Dict[str, Any]:
    """Compute total earned, paid, and due for a worker"""
    # Get all allocations for this worker
    allocations = db.query(JobAllocation).filter(JobAllocation.worker_id == worker_id).all()
    
    earned = Decimal(0)
    
    for alloc in allocations:
        job = alloc.job
        if job.is_finalized and job.snapshot:
            # Use snapshot if finalized
            snapshot_data = json.loads(job.snapshot.snapshot_json)
            for alloc_data in snapshot_data.get("allocations", []):
                if alloc_data.get("allocation_id") == alloc.id:
                    earned += Decimal(str(alloc_data.get("earned", 0)))
                    break
        else:
            # Compute from current data
            receipts = db.query(Receipt).filter(Receipt.job_id == job.id).all()
            totals = get_job_totals(job, receipts, job.settings_version)
            alloc_results = compute_allocations(job, [alloc], totals, job.settings_version)
            if alloc_results:
                earned += alloc_results[0]["earned"]
    
    # Get all payments that are actually paid
    payments = db.query(Payment).filter(
        Payment.worker_id == worker_id,
        Payment.is_paid == True
    ).all()
    paid = sum((Decimal(str(p.amount_paid)) for p in payments), Decimal(0))
    
    due = earned - paid
    
    return {
        "earned": quantize_decimal(earned),
        "paid": quantize_decimal(paid),
        "due": quantize_decimal(due)
    }

def get_dashboard_totals(db: Session) -> Dict[str, Any]:
    """Get dashboard totals across all jobs"""
    jobs = db.query(Job).filter(Job.status != "archived").all()
    
    total_received = Decimal(0)
    total_connects = Decimal(0)
    total_platform_fee = Decimal(0)
    total_paid = Decimal(0)
    
    for job in jobs:
        receipts = db.query(Receipt).filter(Receipt.job_id == job.id).all()
        
        if job.is_finalized and job.snapshot:
            snapshot_data = json.loads(job.snapshot.snapshot_json)
            totals = snapshot_data.get("totals", {})
            total_received += Decimal(str(totals.get("total_received", 0)))
            total_connects += Decimal(str(totals.get("connect_deduction", 0)))
            total_platform_fee += Decimal(str(totals.get("platform_fee", 0)))
        else:
            totals = get_job_totals(job, receipts, job.settings_version)
            total_received += totals["total_received"]
            total_connects += totals["connect_deduction"]
            total_platform_fee += totals["platform_fee"]
    
    # Total paid (only actually paid payments)
    payments = db.query(Payment).filter(Payment.is_paid == True).all()
    total_paid = sum((Decimal(str(p.amount_paid)) for p in payments), Decimal(0))
    
    # Calculate total due (sum of all worker dues)
    workers = db.query(Worker).filter(Worker.is_archived == False).all()
    total_due = Decimal(0)
    for worker in workers:
        worker_totals = compute_worker_totals(worker.id, db)
        total_due += worker_totals["due"]
    
    return {
        "total_received": quantize_decimal(total_received),
        "total_connects": quantize_decimal(total_connects),
        "total_platform_fee": quantize_decimal(total_platform_fee),
        "total_paid": quantize_decimal(total_paid),
        "total_due": quantize_decimal(total_due)
    }

def get_earnings_for_period(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Decimal:
    """Get total earnings (receipts) for a specific date period"""
    jobs = db.query(Job).filter(Job.status != "archived").all()
    
    total_earnings = Decimal(0)
    
    for job in jobs:
        # Build query for receipts
        receipt_query = db.query(Receipt).filter(Receipt.job_id == job.id)
        
        # Apply date filter if provided
        if date_from:
            receipt_query = receipt_query.filter(Receipt.received_date >= date_from)
        if date_to:
            receipt_query = receipt_query.filter(Receipt.received_date <= date_to)
        
        receipts = receipt_query.all()
        
        if job.is_finalized and job.snapshot:
            # For finalized jobs, we need to check if receipts fall within date range
            snapshot_data = json.loads(job.snapshot.snapshot_json)
            snapshot_total = Decimal(str(snapshot_data.get("totals", {}).get("total_received", 0)))
            
            # If date filter is applied, we need to sum only receipts in that range
            if date_from or date_to:
                # Sum only receipts in the date range
                for receipt in receipts:
                    total_earnings += Decimal(str(receipt.amount_received))
            else:
                # No date filter, use snapshot total
                total_earnings += snapshot_total
        else:
            # Sum receipts in the date range
            for receipt in receipts:
                total_earnings += Decimal(str(receipt.amount_received))
    
    return quantize_decimal(total_earnings)

def get_owner_earnings_for_period(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Decimal:
    """Get owner earnings for a specific date period.
    Owner earnings = allocations with worker_id=null + allocations for workers with is_owner=True"""
    # Get owner workers
    owner_workers = db.query(Worker).filter(Worker.is_owner == True, Worker.is_archived == False).all()
    owner_worker_ids = [w.id for w in owner_workers]
    
    jobs = db.query(Job).filter(Job.status != "archived").all()
    
    total_owner_earnings = Decimal(0)
    
    for job in jobs:
        # Get receipts for this job within date range
        receipt_query = db.query(Receipt).filter(Receipt.job_id == job.id)
        if date_from:
            receipt_query = receipt_query.filter(Receipt.received_date >= date_from)
        if date_to:
            receipt_query = receipt_query.filter(Receipt.received_date <= date_to)
        receipts = receipt_query.all()
        
        if not receipts:
            continue
        
        # Get all allocations for this job
        allocations = db.query(JobAllocation).filter(JobAllocation.job_id == job.id).all()
        
        # Filter to owner allocations (worker_id is null OR worker_id is in owner_worker_ids)
        owner_allocations = [
            alloc for alloc in allocations
            if alloc.worker_id is None or alloc.worker_id in owner_worker_ids
        ]
        
        if not owner_allocations:
            continue
        
        if job.is_finalized and job.snapshot:
            # Use snapshot if finalized
            snapshot_data = json.loads(job.snapshot.snapshot_json)
            snapshot_allocations = snapshot_data.get("allocations", [])
            
            # Calculate owner earnings from snapshot
            for snap_alloc in snapshot_allocations:
                alloc_id = snap_alloc.get("allocation_id")
                alloc = next((a for a in owner_allocations if a.id == alloc_id), None)
                if alloc:
                    # Check if receipt date is in range
                    receipt_dates = [r.received_date for r in receipts]
                    if receipt_dates:
                        total_owner_earnings += Decimal(str(snap_alloc.get("earned", 0)))
        else:
            # Compute from current data
            totals = get_job_totals(job, receipts, job.settings_version)
            alloc_results = compute_allocations(job, owner_allocations, totals, job.settings_version)
            for result in alloc_results:
                total_owner_earnings += result["earned"]
    
    return quantize_decimal(total_owner_earnings)
