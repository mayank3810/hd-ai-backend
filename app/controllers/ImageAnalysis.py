from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from typing import Optional
from app.dependencies import get_image_analysis_helper

router = APIRouter(prefix="/api/v1/image-analysis", tags=["Image Analysis"])


@router.post("/process-property-images/{property_id}", response_model=ServerResponse)
async def process_property_images(
    property_id: str,
    batch_id: Optional[str] = Query(None, description="Optional batch ID for tracking"),
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Process all images for a property (both ours and competitors).
    Downloads, resizes, computes hashes, extracts EXIF data, and saves to cache.
    """
    try:
        result = helper.process_images_for_property(property_id, batch_id)
        return Utils.create_response(result, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.get("/checkpoints/{batch_id}", response_model=ServerResponse)
async def get_image_checkpoints(
    batch_id: str,
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Get all image analysis checkpoints for a specific batch.
    """
    try:
        checkpoints = await helper.checkpoints_model.get_checkpoints_by_batch(batch_id)
        # Convert ObjectId to string for JSON serialization
        for checkpoint in checkpoints:
            if '_id' in checkpoint:
                checkpoint['_id'] = str(checkpoint['_id'])
        return Utils.create_response(checkpoints, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.get("/checkpoint/{batch_id}/{image_id}/{side}", response_model=ServerResponse)
async def get_image_checkpoint(
    batch_id: str,
    image_id: str,
    side: str,
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Get a specific image analysis checkpoint.
    """
    try:
        checkpoint = await helper.checkpoints_model.get_checkpoint(batch_id, image_id, side)
        if not checkpoint:
            raise HTTPException(
                status_code=404,
                detail={"data": None, "error": "Checkpoint not found", "success": False}
            )
        # Convert ObjectId to string for JSON serialization
        if '_id' in checkpoint:
            checkpoint['_id'] = str(checkpoint['_id'])
        return Utils.create_response(checkpoint, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.delete("/checkpoints/{batch_id}", response_model=ServerResponse)
async def delete_batch_checkpoints(
    batch_id: str,
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Delete all checkpoints for a specific batch.
    """
    try:
        deleted_count = await helper.checkpoints_model.delete_checkpoints_by_batch(batch_id)
        return Utils.create_response({"deleted_count": deleted_count}, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.post("/find-near-duplicates/{batch_id}", response_model=ServerResponse)
async def find_near_duplicates(
    batch_id: str,
    hamming_threshold: int = Query(8, description="Hamming distance threshold for near-duplicates", ge=0, le=64),
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Find near-duplicates in ImageAnalysisCheckpoints for a batch_id using pHash Hamming distance.
    
    - Groups images by pHash similarity within the threshold
    - Selects best image from each group (higher resolution, smaller file size)
    - Marks others as duplicates in MongoDB
    - Generates JSON report in CACHE_DIR/dedupe/
    """
    try:
        result = helper.find_near_duplicates(batch_id, hamming_threshold)
        return Utils.create_response(result, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.post("/analyze-quality/{batch_id}", response_model=ServerResponse)
async def analyze_image_quality(
    batch_id: str,
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Analyze image quality metrics for all non-duplicate images in a batch.
    
    Computes quality metrics:
    - Brightness (mean of grayscale 0-255)
    - Contrast (stddev of grayscale)
    - Sharpness (variance of Laplacian via OpenCV)
    - Noise proxy (high-frequency energy ratio)
    - White-balance hint (simple Kelvin proxy)
    
    Maps metrics to buckets:
    - Brightness: dark (<90), balanced (90-165), bright (>165)
    - Contrast: low (<45), ok (45-85), high (>85)
    - Sharpness: soft (<50), ok (50-150), crisp (>150)
    - White-balance: cool, neutral, warm
    
    Saves results to MongoDB 'quality' field and generates report in CACHE_DIR/quality/
    """
    try:
        result = helper.analyze_image_quality_for_batch(batch_id)
        return Utils.create_response(result, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.post("/analyze-with-llm/{batch_id}", response_model=ServerResponse)
async def analyze_images_with_llm(
    batch_id: str,
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Analyze all non-duplicate images in a batch using OpenAI vision API (gpt-4o).
    
    For each image, extracts structured facts:
    - Room type classification (bedroom, bathroom, kitchen, etc.)
    - Amenities with confidence scores
    - Selling points
    - Quality issues (dim lighting, clutter, etc.)
    - Quality hints (brightness, contrast, sharpness)
    - Semantic caption
    - Additional notes
    
    Stores results in MongoDB 'AIImagesAnalyses' collection with doc_id format: {batch_id}_{image_id}_{side}
    Generates report in CACHE_DIR/llm_analysis/
    """
    try:
        result = helper.analyze_images_with_llm_for_batch(batch_id)
        return Utils.create_response(result, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.get("/llm-analyses/{batch_id}", response_model=ServerResponse)
async def get_llm_analyses(
    batch_id: str,
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Get all LLM analyses for a specific batch.
    """
    try:
        analyses = await helper.ai_analyses_model.get_analyses_by_batch(batch_id)
        # Convert ObjectId to string for JSON serialization
        for analysis in analyses:
            if '_id' in analysis:
                analysis['_id'] = str(analysis['_id'])
        return Utils.create_response(analyses, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.get("/llm-analysis/{doc_id}", response_model=ServerResponse)
async def get_llm_analysis(
    doc_id: str,
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Get a specific LLM analysis by doc_id.
    """
    try:
        analysis = await helper.ai_analyses_model.get_analysis(doc_id)
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail={"data": None, "error": "LLM analysis not found", "success": False}
            )
        # Convert ObjectId to string for JSON serialization
        if '_id' in analysis:
            analysis['_id'] = str(analysis['_id'])
        return Utils.create_response(analysis, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.post("/pipeline/{property_id}", response_model=ServerResponse)
async def run_image_analysis_pipeline(
    property_id: str,
    batch_id: Optional[str] = Query(None, description="Optional batch ID for tracking"),
    hamming_threshold: int = Query(8, description="Hamming distance threshold for near-duplicates", ge=0, le=64),
    skip_steps: Optional[str] = Query(None, description="Comma-separated steps to skip (e.g., 'llm_analysis,quality_analysis')"),
    enable_llm_analysis: bool = Query(True, description="Whether to run LLM analysis"),
    enable_quality_analysis: bool = Query(True, description="Whether to run quality analysis"),
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Run the complete ImageAnalysis pipeline step by step.
    
    Pipeline Steps:
    1. Image Processing - Download and process images (ours + competitors)
    2. Deduplication - Find and mark near-duplicate images
    3. LLM Analysis - Analyze images with OpenAI vision API (optional)
    4. Quality Analysis - Compute quality metrics (optional)
    
    Returns comprehensive results including timing, success rates, and detailed step results.
    """
    try:
        # Parse skip_steps if provided
        skip_steps_list = []
        if skip_steps:
            skip_steps_list = [step.strip() for step in skip_steps.split(',')]
        
        result = helper.run_image_analysis_pipeline(
            property_id=property_id,
            batch_id=batch_id,
            hamming_threshold=hamming_threshold,
            skip_steps=skip_steps_list,
            enable_llm_analysis=enable_llm_analysis,
            enable_quality_analysis=enable_quality_analysis
        )
        return Utils.create_response(result, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.post("/pipeline/quick/{property_id}", response_model=ServerResponse)
async def run_quick_pipeline(
    property_id: str,
    batch_id: Optional[str] = Query(None, description="Optional batch ID for tracking"),
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Run a quick pipeline with only essential steps (no LLM or quality analysis).
    Useful for testing or when you only need basic image processing and deduplication.
    
    Steps:
    1. Image Processing - Download and process images
    2. Deduplication - Find and mark near-duplicate images
    """
    try:
        result = helper.run_quick_pipeline(property_id, batch_id)
        return Utils.create_response(result, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.post("/pipeline/full/{property_id}", response_model=ServerResponse)
async def run_full_pipeline(
    property_id: str,
    batch_id: Optional[str] = Query(None, description="Optional batch ID for tracking"),
    hamming_threshold: int = Query(8, description="Hamming distance threshold for near-duplicates", ge=0, le=64),
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Run the complete pipeline with all analysis steps.
    
    Steps:
    1. Image Processing - Download and process images
    2. Deduplication - Find and mark near-duplicate images
    3. LLM Analysis - Analyze images with OpenAI vision API
    4. Quality Analysis - Compute quality metrics
    """
    try:
        result = helper.run_full_pipeline(property_id, batch_id, hamming_threshold)
        return Utils.create_response(result, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.get("/pipeline/report/{batch_id}", response_model=ServerResponse)
async def get_pipeline_report(
    batch_id: str,
    helper = Depends(get_image_analysis_helper),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Get the comprehensive pipeline report for a specific batch.
    """
    try:
        import json
        from pathlib import Path
        
        # Try to load the pipeline report from cache
        report_path = helper.cache_dir / "pipeline" / f"{batch_id}.json"
        
        if not report_path.exists():
            raise HTTPException(
                status_code=404,
                detail={"data": None, "error": f"Pipeline report not found for batch {batch_id}", "success": False}
            )
        
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        return Utils.create_response(report, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )
