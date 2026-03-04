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
_speaker_topics_model = None
_speaker_target_audience_model = None
_scraper_service = None


def get_auth_service():
    """Get singleton AuthService instance"""
    global _auth_service
    if _auth_service is None:
        from app.services.Auth import AuthService
        _auth_service = AuthService()
    return _auth_service


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




def get_speaker_profile_model():
    """Get singleton SpeakerProfileModel instance"""
    global _speaker_profile_model
    if _speaker_profile_model is None:
        from app.models.SpeakerProfile import SpeakerProfileModel
        _speaker_profile_model = SpeakerProfileModel()
    return _speaker_profile_model


def get_speaker_topics_model():
    """Get singleton SpeakerTopicsModel instance"""
    global _speaker_topics_model
    if _speaker_topics_model is None:
        from app.models.SpeakerTopics import SpeakerTopicsModel
        _speaker_topics_model = SpeakerTopicsModel()
    return _speaker_topics_model


def get_speaker_target_audience_model():
    """Get singleton SpeakerTargetAudienceModel instance"""
    global _speaker_target_audience_model
    if _speaker_target_audience_model is None:
        from app.models.SpeakerTargetAudience import SpeakerTargetAudienceModel
        _speaker_target_audience_model = SpeakerTargetAudienceModel()
    return _speaker_target_audience_model


def get_scraper_service():
    """Get singleton ScraperRapidAPIService instance (RapidAPI scraper + LLM)."""
    global _scraper_service
    if _scraper_service is None:
        from app.services.ScraperRapidAPI import ScraperRapidAPIService
        _scraper_service = ScraperRapidAPIService()
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
    global _onboarding_status_service, _queue_status_service, _analytics_cues_preset_service, _excel_schedule_service, _speaker_profile_model, _speaker_topics_model, _speaker_target_audience_model, _scraper_service

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
    _speaker_topics_model = None
    _speaker_target_audience_model = None
    _scraper_service = None
