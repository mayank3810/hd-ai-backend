from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Optional, Union, List, Literal, Any
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId

class ReviewInsight(BaseModel):
    type: Literal["DIDNTLIKE", "WISHTOHAVE", "LOVEDTOHAVE"]
    title: str
    description: str

class ReviewSuggestion(BaseModel):
    title: str
    description: str

class AmenityRanking(BaseModel):
    title: str
    description: str

class ImageCaption(BaseModel):
    url: str
    imageId: str
    caption: str
    generatedAt: datetime

class CompetitorData(BaseModel):
    competitorId: str
    competitorName: str
    competitorNumPhotos: int
    competitorReviewsCount: Optional[int] = None
    competitorReviewsScore: Optional[float] = None
    competitorBookingLink: Optional[str] = None
    competitorAirbnbLink: Optional[str] = None
    competitorVrboLink: Optional[str] = None
    competitorCaptionedCount: int = 0
    competitorMissingCaptionCount: int = 0
    # Comparison fields for this specific competitor
    photoGapValue: int = 0
    photoGapStatus: str = "EQUAL"  # "BEHIND", "AHEAD", "EQUAL"
    captionStatusProgress: float = 0.0
    whatGuestsDidntLike: List[ReviewInsight] = Field(default_factory=list)
    whatGuestsWishTheyHad: List[ReviewInsight] = Field(default_factory=list)
    whatGuestsLove: List[ReviewInsight] = Field(default_factory=list)
    improvementSuggestions: List[ReviewInsight] = Field(default_factory=list)
    rankingConversionBoosters: List[AmenityRanking] = Field(default_factory=list)
    topRankingAmenitiesInArea: List[str] = Field(default_factory=list)

class CompetitorComparisonViewSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operator_id: str
    propertyId: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    competitorIds: List[str] = Field(default_factory=list)
    reviewAnalysisOwn: List[ReviewInsight] = Field(default_factory=list)
    reviewAnalysisOwnBooking: List[ReviewInsight] = Field(default_factory=list)
    reviewAnalysisOwnAirbnb: List[ReviewInsight] = Field(default_factory=list)
    reviewAnalysisCompetitor: List[ReviewInsight] = Field(default_factory=list)
    reviewAnalysisCompetitorBooking: List[ReviewInsight] = Field(default_factory=list)
    reviewAnalysisCompetitorAirbnb: List[ReviewInsight] = Field(default_factory=list)
    reviewSuggestionsBasedOnCompetitor: List[ReviewSuggestion] = Field(default_factory=list)
    reviewSuggestionsBasedOnCompetitorBooking: List[ReviewSuggestion] = Field(default_factory=list)
    reviewSuggestionsBasedOnCompetitorAirbnb: List[ReviewSuggestion] = Field(default_factory=list)
    reviewSuggestionsBasedOnOwn: List[ReviewSuggestion] = Field(default_factory=list)
    reviewSuggestionsBasedOnOwnBooking: List[ReviewSuggestion] = Field(default_factory=list)
    reviewSuggestionsBasedOnOwnAirbnb: List[ReviewSuggestion] = Field(default_factory=list)
    conversionBoostersBooking: Optional[Dict[str, Any]] = Field(default_factory=dict)
    conversionBoostersAirbnb: Optional[Dict[str, Any]] = Field(default_factory=dict)
    topAreaAmenitiesMissingBooking: List[Dict[str, Any]] = Field(default_factory=list)
    topAreaAmenitiesMissingAirbnb: List[Dict[str, Any]] = Field(default_factory=list)
    imageCaptionsAirbnb: List[ImageCaption] = Field(default_factory=list)
    imageCaptionsBooking: List[ImageCaption] = Field(default_factory=list)
    imageCaptionsVrbo: List[ImageCaption] = Field(default_factory=list)
    aiPhotoAnalysisBooking: Optional[dict] = None
    aiPhotoAnalysisAirbnb: Optional[dict] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class CompetitorComparisonCreateSchema(BaseModel):
    operatorId: str
    propertyId: str

    class Config:
        populate_by_name = True

class CompetitorComparisonUpdateSchema(BaseModel):
    competitors: Optional[List[CompetitorData]] = None
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class ReviewsAnalysisUpdateSchema(BaseModel):
    whatGuestsDidntLike: Optional[List[ReviewInsight]] = None
    whatGuestsWishTheyHad: Optional[List[ReviewInsight]] = None
    whatGuestsLove: Optional[List[ReviewInsight]] = None
    improvementSuggestions: Optional[List[ReviewInsight]] = None

    class Config:
        populate_by_name = True

class ReviewsAnalysisResponseSchema(BaseModel):
    whatGuestsDidntLike: List[ReviewInsight] = Field(default_factory=list)
    whatGuestsWishTheyHad: List[ReviewInsight] = Field(default_factory=list)
    whatGuestsLove: List[ReviewInsight] = Field(default_factory=list)
    improvementSuggestions: List[ReviewInsight] = Field(default_factory=list)

    class Config:
        populate_by_name = True
