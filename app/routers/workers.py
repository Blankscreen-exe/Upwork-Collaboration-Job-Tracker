from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import Worker
from app.schemas import WorkerCreate, WorkerUpdate
from app.services.calculations import compute_worker_totals
from app.dependencies import get_db_session
from app.utils import generate_worker_code

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/workers", response_class=HTMLResponse)
async def list_workers(request: Request, db: Session = Depends(get_db_session)):
    workers = db.query(Worker).filter(Worker.is_archived == False).order_by(Worker.name).all()
    return templates.TemplateResponse("workers/list.html", {
        "request": request,
        "workers": workers
    })

@router.get("/workers/new", response_class=HTMLResponse)
async def new_worker_form(request: Request, db: Session = Depends(get_db_session)):
    next_code = generate_worker_code(db)
    return templates.TemplateResponse("workers/form.html", {
        "request": request,
        "worker": None,
        "suggested_code": next_code
    })

@router.post("/workers/new")
async def create_worker(
    request: Request,
    worker_code: str = Form(None),
    name: str = Form(...),
    contact: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db_session)
):
    # Auto-generate code if not provided
    if not worker_code or worker_code.strip() == "":
        worker_code = generate_worker_code(db)
    
    # Check if worker_code already exists
    existing = db.query(Worker).filter(Worker.worker_code == worker_code).first()
    if existing:
        next_code = generate_worker_code(db)
        return templates.TemplateResponse("workers/form.html", {
            "request": request,
            "worker": None,
            "suggested_code": next_code,
            "error": f"Worker code {worker_code} already exists"
        }, status_code=400)
    
    worker = Worker(
        worker_code=worker_code,
        name=name,
        contact=contact if contact else None,
        notes=notes if notes else None
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    
    return RedirectResponse(url=f"/workers/{worker.id}", status_code=303)

@router.get("/workers/{worker_id}", response_class=HTMLResponse)
async def worker_detail(request: Request, worker_id: int, db: Session = Depends(get_db_session)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Get worker totals
    totals = compute_worker_totals(worker_id, db)
    
    # Get allocations grouped by job
    allocations_by_job = {}
    for alloc in worker.allocations:
        if alloc.job.status != "archived":
            if alloc.job_id not in allocations_by_job:
                allocations_by_job[alloc.job_id] = {
                    "job": alloc.job,
                    "allocations": []
                }
            allocations_by_job[alloc.job_id]["allocations"].append(alloc)
    
    # Get payments
    payments = sorted(worker.payments, key=lambda p: p.paid_date, reverse=True)
    
    return templates.TemplateResponse("workers/detail.html", {
        "request": request,
        "worker": worker,
        "totals": totals,
        "allocations_by_job": allocations_by_job.values(),
        "payments": payments
    })

@router.get("/workers/{worker_id}/edit", response_class=HTMLResponse)
async def edit_worker_form(request: Request, worker_id: int, db: Session = Depends(get_db_session)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    return templates.TemplateResponse("workers/form.html", {
        "request": request,
        "worker": worker
    })

@router.post("/workers/{worker_id}/edit")
async def update_worker(
    request: Request,
    worker_id: int,
    worker_code: str = Form(...),
    name: str = Form(...),
    contact: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db_session)
):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Check if worker_code already exists (for other workers)
    existing = db.query(Worker).filter(Worker.worker_code == worker_code, Worker.id != worker_id).first()
    if existing:
        return templates.TemplateResponse("workers/form.html", {
            "request": request,
            "worker": worker,
            "error": f"Worker code {worker_code} already exists"
        }, status_code=400)
    
    worker.worker_code = worker_code
    worker.name = name
    worker.contact = contact if contact else None
    worker.notes = notes if notes else None
    db.commit()
    
    return RedirectResponse(url=f"/workers/{worker.id}", status_code=303)

@router.post("/workers/{worker_id}/archive")
async def archive_worker(worker_id: int, db: Session = Depends(get_db_session)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    worker.is_archived = True
    db.commit()
    
    return RedirectResponse(url="/workers", status_code=303)
