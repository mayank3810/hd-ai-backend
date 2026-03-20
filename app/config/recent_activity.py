"""Recent activity feed: `type` values stored on each document in recentActivities."""

RECENT_ACTIVITY_TYPE_SCRAPER = "scraper"
RECENT_ACTIVITY_TYPE_OPPORTUNITIES = "opportunities"
RECENT_ACTIVITY_TYPE_GOOGLE_QUERIES = "google_queries"

MESSAGE_SCRAPER_ADDED = "New scraper added"
MESSAGE_GOOGLE_QUERIES_ADDED = "New Google queries added"


def message_opportunities_added(count: int) -> str:
    """Feed line when opportunities were saved (direct URL scrape or aggregated Google query run)."""
    n = max(0, int(count))
    return f"New opportunities added ({n})"
