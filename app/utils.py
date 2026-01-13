from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Worker, Job, Payment

def generate_worker_code(db: Session) -> str:
    """Generate next worker code (W01, W02, etc.)"""
    # Get the highest numeric part
    last_worker = db.query(Worker).order_by(Worker.id.desc()).first()
    if not last_worker:
        return "W01"
    
    # Try to extract number from existing codes
    import re
    max_num = 0
    workers = db.query(Worker).all()
    for worker in workers:
        match = re.match(r'W(\d+)', worker.worker_code)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    return f"W{max_num + 1:02d}"

def generate_job_code(db: Session) -> str:
    """Generate next job code (J01, J02, etc.)"""
    # Get the highest numeric part
    last_job = db.query(Job).order_by(Job.id.desc()).first()
    if not last_job:
        return "J01"
    
    # Try to extract number from existing codes
    import re
    max_num = 0
    jobs = db.query(Job).all()
    for job in jobs:
        match = re.match(r'J(\d+)', job.job_code)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    return f"J{max_num + 1:02d}"

def generate_payment_code(db: Session) -> str:
    """Generate next payment code (P0001, P0002, etc.)"""
    # Get the highest numeric part
    last_payment = db.query(Payment).order_by(Payment.id.desc()).first()
    if not last_payment:
        return "P0001"
    
    # Try to extract number from existing codes
    import re
    max_num = 0
    payments = db.query(Payment).all()
    for payment in payments:
        match = re.match(r'P(\d+)', payment.payment_code)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    return f"P{max_num + 1:04d}"
