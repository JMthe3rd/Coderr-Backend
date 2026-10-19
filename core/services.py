"""Aggregate public statistics across marketplace applications."""

from django.db.models import Avg, Count

from auth_app.models import UserProfile
from offers_app.models import Offer
from reviews_app.models import Review


def get_base_info():
    """Return global counts and a one-decimal mean of all review ratings."""
    reviews = Review.objects.aggregate(
        count=Count("id"), average=Avg("rating")
    )
    return {
        "review_count": reviews["count"],
        "average_rating": round(reviews["average"] or 0.0, 1),
        "business_profile_count": UserProfile.objects.filter(
            type="business"
        ).count(),
        "offer_count": Offer.objects.count(),
    }
