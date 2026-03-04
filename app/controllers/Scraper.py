"""
API for scrape-and-extract speaking opportunities workflow.
Uses RapidAPI AI Content Scraper (single URL, no crawling).
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.middleware.JWTVerification import jwt_validator
from app.schemas.Scraper import CrawlForOpportunitiesRequest
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.dependencies import get_scraper_service


router = APIRouter(prefix="/api/v1/scraper", tags=["scraper"])


@router.post("/crawl", response_model=ServerResponse)
async def create_scrape_job(
    body: CrawlForOpportunitiesRequest,
    background_tasks: BackgroundTasks,
    service=Depends(get_scraper_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    """
    Create a pending scrape job. Returns job ID immediately.
    Scraping via RapidAPI and LLM extraction run in the background.
    """
    try:
        user_id = jwt_payload.get("user_id") or jwt_payload.get("id") or str(jwt_payload.get("_id", ""))
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        job_id = await service.create_scrape_job(url=body.url, user_id=user_id)
        background_tasks.add_task(service.run_scrape_and_extract, job_id)
        return Utils.create_response({"id": job_id}, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/{scraper_id}", response_model=ServerResponse)
async def get_scrape_job(
    scraper_id: str,
    service=Depends(get_scraper_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    """Get scrape job status and opportunities by ID."""
    try:
        user_id = jwt_payload.get("user_id") or jwt_payload.get("id") or str(jwt_payload.get("_id", ""))
        doc = await service.get_by_id(scraper_id, user_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Scrape job not found")
        return Utils.create_response(doc, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
