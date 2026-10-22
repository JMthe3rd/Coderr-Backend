"""Public platform summary endpoint."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services import get_base_info


class BaseInfoView(APIView):
    """Expose aggregate counts without requiring an account."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Return review count/mean, business profile count and offer count."""
        return Response(get_base_info())
