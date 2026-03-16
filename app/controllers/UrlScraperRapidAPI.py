"""
Controller for URL scraping via RapidAPI.
Separate from Scraper controller - no connection with existing Scraper/Scrapers.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.schemas.Opportunity import UrlScrapeCreateSchema
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.dependencies import get_url_scraper_rapidapi_service
from app.middleware.JWTVerification import jwt_validator
from app.services.UrlScraperRapidAPI import is_pdf_url

router = APIRouter(prefix="/api/v1/url-scraper", tags=["URL Scraper (RapidAPI)"])


@router.post("/", response_model=ServerResponse, status_code=201)
async def create_url_scrape(
    data: UrlScrapeCreateSchema,
    background_tasks: BackgroundTasks,
    service=Depends(get_url_scraper_rapidapi_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    """
    Submit a URL for scraping. Saves url+createdAt to UrlCollection immediately.
    Background task scrapes the URL, extracts opportunities via LLM, and inserts
    each opportunity into the Opportunities collection.
    """
    try:
        url = data.url.strip()
        if not url:
            raise HTTPException(
                status_code=400,
                detail={"data": None, "error": "URL is required", "success": False},
            )
        if is_pdf_url(url):
            raise HTTPException(
                status_code=400,
                detail={"data": None, "error": "PDF URLs are not scraped", "success": False},
            )

        user_id = jwt_payload.get("id")
        topics = getattr(data, "topics", None) if data else None
        url_collection_id = await service.create_url_scrape_job(url, user_id=user_id, topics=topics)
        background_tasks.add_task(service.run_scrape_and_extract, url_collection_id, url)

        return Utils.create_response(
            {"urlCollectionId": url_collection_id, "url": url, "message": "URL submitted. Processing in background."},
            True,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/{url_collection_id}", response_model=ServerResponse)
async def get_url_collection(
    url_collection_id: str,
    service=Depends(get_url_scraper_rapidapi_service),
):
    """Get a UrlCollection entry by ID (url and createdAt only)."""
    try:
        doc = await service.get_url_collection_by_id(url_collection_id)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"data": None, "error": "UrlCollection not found", "success": False},
            )
        # Convert _id to string for JSON
        doc["_id"] = str(doc["_id"])
        return Utils.create_response(doc, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )
