"""Page-number pagination for the public offer listing."""

from rest_framework.pagination import PageNumberPagination


class OfferPagination(PageNumberPagination):
    """Use six offers by default and at most one hundred per page."""

    page_size = 6
    page_size_query_param = "page_size"
    max_page_size = 100
