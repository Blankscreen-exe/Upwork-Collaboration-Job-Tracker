from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.services.calculations import get_dashboard_totals, compute_worker_totals
from app.models import Worker, Job
from app.dependencies import get_db_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db_session)):
    # Get dashboard totals
    totals = get_dashboard_totals(db)
    
    # Get top due workers
    workers = db.query(Worker).filter(Worker.is_archived == False).all()
    worker_dues = []
    for worker in workers:
        worker_totals = compute_worker_totals(worker.id, db)
        if worker_totals["due"] > 0:
            worker_dues.append({
                "worker": worker,
                "due": worker_totals["due"]
            })
    
    # Sort by due amount descending
    worker_dues.sort(key=lambda x: x["due"], reverse=True)
    
    # Get recent jobs
    recent_jobs = db.query(Job).filter(Job.status != "archived").order_by(desc(Job.created_at)).limit(10).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "totals": totals,
        "worker_dues": worker_dues[:10],  # Top 10
        "recent_jobs": recent_jobs
    })
