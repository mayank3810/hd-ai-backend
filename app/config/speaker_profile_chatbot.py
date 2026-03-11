"""
Allowed values for Speaker Profile Chatbot (conversation-based onboarding).
Topics and Target Audiences are validated against these names; DB lookups provide _id/slug.
"""

# Canonical allowed topic names (exact match, case-sensitive for storage)
TOPICS = [
    "Executive Leadership",
    "Nonprofit",
    "Technology",
    "Customer Experience",
    "Financial Services",
    "Human Resources (HR)",
    "Public Relations (PR)",
    "B2C",
    "Developer",
    "Marketing",
    "Communications",
    "Retail",
    "AI",
    "Data Science",
    "Education",
    "B2B",
    "EdTech",
    "E-Commerce",
    "UX/UI",
    "Women In Tech",
]

# Canonical allowed speaking formats
SPEAKING_FORMATS = [
    "Keynote",
    "Panel Discussion",
    "Workshop",
    "Solo Talk",
]

# Canonical allowed delivery modes (matches speaker_profile_steps)
DELIVERY_MODE = [
    "Virtual",
    "In-person",
    "Hybrid",
]

# Canonical allowed target audience names
TARGET_AUDIENCES = [
    "General Audience",
    "Managers",
    "Technical Professionals",
    "Sales Teams",
    "Executives",
    "Corporate Teams",
    "Women Leaders",
    "Startups",
    "Small Businesses",
    "HR Professionals",
    "Entrepreneurs",
    "Students",
]

# Mandatory fields for speaker profile (must be filled before "complete")
# email and full_name are required for initial creation
MANDATORY_FIELDS = [
    "full_name",
    "email",
    "topics",
    "speaking_formats",
    "delivery_mode",
    "talk_description",
    "target_audiences",
]

# Optional fields (asked after all mandatory are filled)
OPTIONAL_FIELDS = [
    "linkedin_url",
    "past_speaking_examples",
    "video_links",
    "key_takeaways",
    "name_salutation",
    "bio",
    "twitter",
    "facebook",
    "address_city",
    "address_state",
    "address_country",
    "phone_country_code",
    "phone_number",
    "professional_memberships",
    "preferred_speaking_time",
]
