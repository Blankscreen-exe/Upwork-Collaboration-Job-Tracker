from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any
import json
from sqlalchemy.orm import Session
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
