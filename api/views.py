import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.repo import SkuRepo, TokenRepo, ProductRepo

logger = logging.getLogger(__name__)


class GetSkuWrapper(APIView):
    permission_classes = (IsAuthenticated,)
    view_factory = None
    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        code, res = SkuRepo.get_sku(data)
        return Response(res, status=code)

class PushSkuWrapper(APIView):
    permission_classes = (IsAuthenticated,)
    view_factory = None

    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        code, res = SkuRepo.push_sku(data)
        return Response(res, status=code)


class GetTokenWrapper(APIView):
    permission_classes = (IsAuthenticated,)
    view_factory = None

    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        user = request.user
        code, res = TokenRepo.get_token(data, user)
        return Response(res, status=code)

class PushTokenWrapper(APIView):
    permission_classes = (IsAuthenticated,)
    view_factory = None

    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        user = request.user
        code, res = TokenRepo.push_token(data, user)
        return Response(res, status=code)


class ExportWrapper(APIView):
    permission_classes = (IsAuthenticated,)
    view_factory = None

    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        code, res = ProductRepo.get_export(data)
        return Response(res, status=code)
