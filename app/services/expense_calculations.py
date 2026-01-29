from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import date, datetime, timedelta
from calendar import monthrange
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from app.models import Expense, Receipt, Job, JobAllocation, Worker
from app.services.calculations import quantize_decimal, get_earnings_for_period, get_job_totals, compute_allocations
import json

def get_expense_totals(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Decimal:
    """Sum all expenses within date range (inclusive). If dates are None, return total for all expenses."""
    query = db.query(Expense)
    
    if date_from:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to:
        query = query.filter(Expense.expense_date <= date_to)
    
    expenses = query.all()
    total = sum((Decimal(str(e.amount)) for e in expenses), Decimal(0))
    return quantize_decimal(total)

def get_expenses_by_month(db: Session, year: int, month: int) -> Decimal:
    """Get total expenses for specific month"""
    # Get first and last day of the month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    return get_expense_totals(db, date_from=first_day, date_to=last_day)

def _calculate_owner_earnings_for_receipts(db: Session, receipts: list) -> Decimal:
    """Calculate owner earnings from a list of receipts"""
    if not receipts:
        return Decimal(0)
    
    # Get owner workers
    owner_workers = db.query(Worker).filter(Worker.is_owner == True, Worker.is_archived == False).all()
    owner_worker_ids = [w.id for w in owner_workers]
    
    total_owner_earnings = Decimal(0)
    
    # Group receipts by job
    jobs_receipts = {}
    for receipt in receipts:
        if receipt.job_id not in jobs_receipts:
            jobs_receipts[receipt.job_id] = []
        jobs_receipts[receipt.job_id].append(receipt)
    
    for job_id, job_receipts in jobs_receipts.items():
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status == "archived":
            continue
        
        # Get all allocations for this job
        allocations = db.query(JobAllocation).filter(JobAllocation.job_id == job_id).all()
        
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
            snapshot_total = Decimal(str(snapshot_data.get("totals", {}).get("total_received", 0)))
            
            # Calculate owner earnings from snapshot
            total_received = sum((Decimal(str(r.amount_received)) for r in job_receipts), Decimal(0))
            
            if snapshot_total > 0 and total_received > 0:
                # Calculate proportional share
                receipt_ratio = total_received / snapshot_total
                
                for snap_alloc in snapshot_allocations:
                    alloc_id = snap_alloc.get("allocation_id")
                    alloc = next((a for a in owner_allocations if a.id == alloc_id), None)
                    if alloc:
                        # Proportional share based on receipt amounts
                        owner_share = receipt_ratio * Decimal(str(snap_alloc.get("earned", 0)))
                        total_owner_earnings += quantize_decimal(owner_share)
        else:
            # Compute from current data
            totals = get_job_totals(job, job_receipts, job.settings_version)
            alloc_results = compute_allocations(job, owner_allocations, totals, job.settings_version)
            for result in alloc_results:
                total_owner_earnings += result["earned"]
    
    return quantize_decimal(total_owner_earnings)

def get_expense_chart_data(db: Session, date_from: date, date_to: date) -> Dict[str, Any]:
    """Returns data structure for Chart.js. Daily breakdown for <=30 days, monthly for >30 days.
    Includes expenses, total earnings, and owner earnings."""
    days_diff = (date_to - date_from).days + 1
    
    if days_diff <= 30:
        # Daily breakdown
        labels = []
        expenses_data = []
        earnings_data = []
        owner_earnings_data = []
        
        current_date = date_from
        while current_date <= date_to:
            labels.append(current_date.strftime("%m/%d"))
            
            # Get expenses for this day
            day_expenses = db.query(Expense).filter(Expense.expense_date == current_date).all()
            day_total = sum((Decimal(str(e.amount)) for e in day_expenses), Decimal(0))
            expenses_data.append(float(quantize_decimal(day_total)))
            
            # Get earnings for this day (from receipts)
            day_receipts = db.query(Receipt).filter(Receipt.received_date == current_date).all()
            day_earnings = sum((Decimal(str(r.amount_received)) for r in day_receipts), Decimal(0))
            earnings_data.append(float(quantize_decimal(day_earnings)))
            
            # Get owner earnings for this day
            day_owner_earnings = _calculate_owner_earnings_for_receipts(db, day_receipts)
            owner_earnings_data.append(float(day_owner_earnings))
            
            current_date += timedelta(days=1)
        
        return {
            "labels": labels,
            "expenses": expenses_data,
            "earnings": earnings_data,
            "owner_earnings": owner_earnings_data
        }
    else:
        # Monthly breakdown
        labels = []
        expenses_data = []
        earnings_data = []
        owner_earnings_data = []
        
        current_date = date(date_from.year, date_from.month, 1)
        end_date = date(date_to.year, date_to.month, 1)
        
        while current_date <= end_date:
            year = current_date.year
            month = current_date.month
            
            # Get first and last day of this month within the range
            month_start = max(date(year, month, 1), date_from)
            month_end = min(date(year, month, monthrange(year, month)[1]), date_to)
            
            labels.append(current_date.strftime("%b %Y"))
            
            # Get expenses for this month
            month_expenses = db.query(Expense).filter(
                and_(
                    Expense.expense_date >= month_start,
                    Expense.expense_date <= month_end
                )
            ).all()
            month_total = sum((Decimal(str(e.amount)) for e in month_expenses), Decimal(0))
            expenses_data.append(float(quantize_decimal(month_total)))
            
            # Get earnings for this month
            month_receipts = db.query(Receipt).filter(
                and_(
                    Receipt.received_date >= month_start,
                    Receipt.received_date <= month_end
                )
            ).all()
            month_earnings = sum((Decimal(str(r.amount_received)) for r in month_receipts), Decimal(0))
            earnings_data.append(float(quantize_decimal(month_earnings)))
            
            # Get owner earnings for this month
            month_owner_earnings = _calculate_owner_earnings_for_receipts(db, month_receipts)
            owner_earnings_data.append(float(month_owner_earnings))
            
            # Move to next month
            if month == 12:
                current_date = date(year + 1, 1, 1)
            else:
                current_date = date(year, month + 1, 1)
        
        return {
            "labels": labels,
            "expenses": expenses_data,
            "earnings": earnings_data,
            "owner_earnings": owner_earnings_data
        }

def calculate_profit(owner_earnings: Decimal, expenses: Decimal) -> Decimal:
    """Calculate profit: owner earnings - expenses"""
    return quantize_decimal(owner_earnings - expenses)

def calculate_margin(profit: Decimal, owner_earnings: Decimal) -> Decimal:
    """Calculate margin percentage: (profit / owner_earnings) * 100. Returns 0 if owner_earnings <= 0."""
    if owner_earnings <= 0:
        return quantize_decimal(Decimal(0))
    
    margin = (profit / owner_earnings) * Decimal(100)
    return quantize_decimal(margin)
