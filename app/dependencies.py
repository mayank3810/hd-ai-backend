"""
Singleton dependencies for resource management.
Prevents creating multiple heavy resources on every API request.
"""
from typing import Optional

# Global singletons - Services
_auth_service = None
_property_service = None
_filter_preset_service = None
_export_service = None
_listings_service = None
_operator_service = None
_pricelabs_service = None
_pricelabs_admin_service = None
_airbnb_admin_service = None
_booking_admin_service = None
_competitor_comparison_service = None
_competitor_property_service = None
_profile_service = None
_common_service = None
_background_mapping_service = None
_image_caption_service = None
_booking_service = None
_airbnb_service = None
_image_analysis_helper = None
_temporary_competitor_service = None
_deployment_cues_service = None
_cue_properties_service = None
_onboarding_status_service = None
_queue_status_service = None
_analytics_cues_preset_service = None
_excel_schedule_service = None
_speaker_profile_model = None
_scraper_service = None


def get_auth_service():
    """Get singleton AuthService instance"""
    global _auth_service
    if _auth_service is None:
        from app.services.Auth import AuthService
        _auth_service = AuthService()
    return _auth_service


def get_property_service():
    """Get singleton PropertyService instance"""
    global _property_service
    if _property_service is None:
        from app.services.Property import PropertyService
        _property_service = PropertyService()
    return _property_service


def get_filter_preset_service():
    """Get singleton FilterPresetService instance"""
    global _filter_preset_service
    if _filter_preset_service is None:
        from app.services.FilterPreset import FilterPresetService
        _filter_preset_service = FilterPresetService()
    return _filter_preset_service


def get_export_service():
    """Get singleton ExportService instance"""
    global _export_service
    if _export_service is None:
        from app.services.Export import ExportService
        _export_service = ExportService()
    return _export_service


def get_listings_service():
    """Get singleton ListingsService instance"""
    global _listings_service
    if _listings_service is None:
        from app.services.Listings import ListingsService
        _listings_service = ListingsService()
    return _listings_service


def get_operator_service():
    """Get singleton OperatorService instance"""
    global _operator_service
    if _operator_service is None:
        from app.services.Operator import OperatorService
        _operator_service = OperatorService()
    return _operator_service


def get_pricelabs_service():
    """Get singleton PricelabsService instance"""
    global _pricelabs_service
    if _pricelabs_service is None:
        from app.services.Pricelabs import PricelabsService
        _pricelabs_service = PricelabsService()
    return _pricelabs_service


def get_pricelabs_admin_service():
    """Get singleton PricelabsAdminService instance"""
    global _pricelabs_admin_service
    if _pricelabs_admin_service is None:
        from app.services.PricelabsAdmin import PricelabsAdminService
        _pricelabs_admin_service = PricelabsAdminService()
    return _pricelabs_admin_service


def get_airbnb_admin_service():
    """Get singleton AirbnbAdminService instance"""
    global _airbnb_admin_service
    if _airbnb_admin_service is None:
        from app.services.AirbnbAdmin import AirbnbAdminService
        _airbnb_admin_service = AirbnbAdminService()
    return _airbnb_admin_service


def get_booking_admin_service():
    """Get singleton BookingAdminService instance"""
    global _booking_admin_service
    if _booking_admin_service is None:
        from app.services.BookingAdmin import BookingAdminService
        _booking_admin_service = BookingAdminService()
    return _booking_admin_service


def get_competitor_comparison_service():
    """Get singleton CompetitorComparisonService instance"""
    global _competitor_comparison_service
    if _competitor_comparison_service is None:
        from app.services.CompetitorComparison import CompetitorComparisonService
        _competitor_comparison_service = CompetitorComparisonService()
    return _competitor_comparison_service


def get_competitor_property_service():
    """Get singleton CompetitorPropertyService instance"""
    global _competitor_property_service
    if _competitor_property_service is None:
        from app.services.CompetitorProperty import CompetitorPropertyService
        _competitor_property_service = CompetitorPropertyService()
    return _competitor_property_service


def get_profile_service():
    """Get singleton ProfileService instance"""
    global _profile_service
    if _profile_service is None:
        from app.services.Profile import ProfileService
        _profile_service = ProfileService()
    return _profile_service


def get_common_service():
    """Get singleton CommonService instance"""
    global _common_service
    if _common_service is None:
        from app.services.Common import CommonService
        _common_service = CommonService()
    return _common_service


# def get_background_mapping_service():
#     """Get singleton BackgroundMappingService instance"""
#     global _background_mapping_service
#     if _background_mapping_service is None:
#         from app.services.BackgroundMapping import BackgroundMappingService
#         _background_mapping_service = BackgroundMappingService()
#     return _background_mapping_service


def get_image_caption_service():
    """Get singleton ImageCaptionService instance"""
    global _image_caption_service
    if _image_caption_service is None:
        from app.services.ImageCaption import ImageCaptionService
        _image_caption_service = ImageCaptionService()
    return _image_caption_service


def get_booking_service():
    """Get singleton BookingService instance"""
    global _booking_service
    if _booking_service is None:
        from app.services.Booking import BookingService
        _booking_service = BookingService()
    return _booking_service


def get_airbnb_service():
    """Get singleton AirbnbService instance"""
    global _airbnb_service
    if _airbnb_service is None:
        from app.services.Airbnb import AirbnbService
        _airbnb_service = AirbnbService()
    return _airbnb_service


def get_image_analysis_helper():
    """Get singleton ImageAnalysisHelper instance"""
    global _image_analysis_helper
    if _image_analysis_helper is None:
        from app.helpers.ImageAnalysis import ImageAnalysisHelper
        _image_analysis_helper = ImageAnalysisHelper()
    return _image_analysis_helper


def get_temporary_competitor_service():
    """Get singleton TemporaryCompetitorsService instance"""
    global _temporary_competitor_service
    if _temporary_competitor_service is None:
        from app.services.TemporaryCompetitors import TemporaryCompetitorsService
        _temporary_competitor_service = TemporaryCompetitorsService()
    return _temporary_competitor_service


def get_deployment_cues_service():
    """Get singleton DeploymentCuesService instance"""
    global _deployment_cues_service
    if _deployment_cues_service is None:
        from app.services.DeploymentCues import DeploymentCuesService
        _deployment_cues_service = DeploymentCuesService()
    return _deployment_cues_service
def get_cue_properties_service():
    """Get singleton CuePropertiesService instance"""
    global _cue_properties_service
    if _cue_properties_service is None:
        from app.services.CueProperties import CuePropertiesService
        _cue_properties_service = CuePropertiesService()
    return _cue_properties_service

def get_onboarding_status_service():
    """Get singleton OnboardingStatusService instance"""
    global _onboarding_status_service
    if _onboarding_status_service is None:
        from app.services.OnboardingStatus import OnboardingStatusService
        _onboarding_status_service = OnboardingStatusService()
    return _onboarding_status_service

def get_queue_status_service():
    """Get singleton QueueStatusService instance"""
    global _queue_status_service
    if _queue_status_service is None:
        from app.services.QueueStatus import QueueStatusService
        _queue_status_service = QueueStatusService()
    return _queue_status_service

def get_analytics_cues_preset_service():
    """Get singleton AnalyticsCuesPresetService instance"""
    global _analytics_cues_preset_service
    if _analytics_cues_preset_service is None:
        from app.services.AnalyticsCuesPreset import AnalyticsCuesPresetService
        _analytics_cues_preset_service = AnalyticsCuesPresetService()
    return _analytics_cues_preset_service

def get_excel_schedule_service():
    """Get singleton ExcelScheduleService instance"""
    global _excel_schedule_service
    if _excel_schedule_service is None:
        from app.services.ExcelSchedule import ExcelScheduleService
        _excel_schedule_service = ExcelScheduleService()
    return _excel_schedule_service


def get_speaker_profile_model():
    """Get singleton SpeakerProfileModel instance"""
    global _speaker_profile_model
    if _speaker_profile_model is None:
        from app.models.SpeakerProfile import SpeakerProfileModel
        _speaker_profile_model = SpeakerProfileModel()
    return _speaker_profile_model


def get_scraper_service():
    """Get singleton ScraperService instance"""
    global _scraper_service
    if _scraper_service is None:
        from app.services.Scraper import ScraperService
        _scraper_service = ScraperService()
    return _scraper_service


def cleanup_resources():
    """
    Cleanup all singleton resources. Call this on application shutdown.
    """
    global _auth_service, _property_service, _filter_preset_service, _export_service
    global _listings_service, _operator_service, _pricelabs_service, _pricelabs_admin_service
    global _airbnb_admin_service, _booking_admin_service, _competitor_comparison_service
    global _competitor_property_service, _profile_service, _common_service
    global _background_mapping_service, _image_caption_service, _booking_service, _airbnb_service
    global _image_analysis_helper, _temporary_competitor_service, _deployment_cues_service
    global _image_analysis_helper, _temporary_competitor_service, _cue_properties_service
    global _onboarding_status_service, _queue_status_service, _analytics_cues_preset_service, _excel_schedule_service, _speaker_profile_model, _scraper_service

    # Reset all services
    _auth_service = None
    _property_service = None
    _filter_preset_service = None
    _export_service = None
    _listings_service = None
    _operator_service = None
    _pricelabs_service = None
    _pricelabs_admin_service = None
    _airbnb_admin_service = None
    _booking_admin_service = None
    _competitor_comparison_service = None
    _competitor_property_service = None
    _profile_service = None
    _common_service = None
    _background_mapping_service = None
    _image_caption_service = None
    _booking_service = None
    _airbnb_service = None
    _image_analysis_helper = None
    _temporary_competitor_service = None
    _deployment_cues_service = None
    _cue_properties_service = None
    _onboarding_status_service = None
    _queue_status_service = None
    _analytics_cues_preset_service = None
    _excel_schedule_service = None
    _speaker_profile_model = None
    _scraper_service = None
