"""
Seed script for speakerTopics and speakerTargetAudeince collections.
Run from project root: python scripts/seed_speaker_topics_audience.py
Requires: MONGODB_CONNECTION_STRING and DB_NAME in .env

Slug format: lowercase, "&" -> "and", spaces -> hyphens.
  e.g. Artificial Intelligence -> artificial-intelligence
       Diversity & Inclusion -> diversity-and-inclusion
       HR Professionals -> hr-professionals
"""
import asyncio
import os
import re
import sys
from typing import List

# Allow importing app modules when run from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

# Collections: speakerTopics, speakerTargetAudeince
SPEAKER_TOPICS_COLLECTION = "speakerTopics"
SPEAKER_TARGET_AUDIENCE_COLLECTION = "speakerTargetAudeince"

TOPICS = [
    "Leadership",
    "Entrepreneurship",
    "Artificial Intelligence",
    "Marketing",
    "Sales",
    "Personal Development",
    "Innovation",
    "Diversity & Inclusion",
    "Mental Health",
    "Finance",
    "Sustainability",
    "Career Growth",
]

TARGET_AUDIENCES = [
    "Executives",
    "Managers",
    "Entrepreneurs",
    "Corporate Teams",
    "Startups",
    "Small Businesses",
    "Students",
    "Women Leaders",
    "Technical Professionals",
    "Sales Teams",
    "HR Professionals",
    "General Audience",
]


def name_to_slug(name: str) -> str:
    """Convert name to URL-friendly slug: lowercase, spaces and '&' to hyphens."""
    s = name.strip().lower()
    s = re.sub(r"\s*&\s*", "-and-", s)
    s = re.sub(r"[^\w\-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def build_documents(names: List[str]):
    """Build list of docs with _id (ObjectId), name, slug."""
    return [
        {"_id": ObjectId(), "name": name, "slug": name_to_slug(name)}
        for name in names
    ]


async def main():
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    db_name = os.getenv("DB_NAME")

    if not connection_string or not db_name:
        print("Missing MONGODB_CONNECTION_STRING or DB_NAME in .env")
        sys.exit(1)

    from app.helpers.Database import MongoDB

    MongoDB.connect(connection_string)
    db = MongoDB.get_database(db_name)

    topics_coll = db[SPEAKER_TOPICS_COLLECTION]
    audience_coll = db[SPEAKER_TARGET_AUDIENCE_COLLECTION]

    topic_docs = build_documents(TOPICS)
    audience_docs = build_documents(TARGET_AUDIENCES)

    await topics_coll.insert_many(topic_docs)
    await audience_coll.insert_many(audience_docs)

    print("Inserted %d documents into %s" % (len(topic_docs), SPEAKER_TOPICS_COLLECTION))
    for d in topic_docs:
        print("  - %s -> slug: %s" % (d["name"], d["slug"]))

    print("\nInserted %d documents into %s" % (len(audience_docs), SPEAKER_TARGET_AUDIENCE_COLLECTION))
    for d in audience_docs:
        print("  - %s -> slug: %s" % (d["name"], d["slug"]))

    if MongoDB.client:
        MongoDB.client.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
