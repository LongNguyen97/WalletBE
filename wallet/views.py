import logging

from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.serializers import jwt_payload_handler, jwt_encode_handler
from rest_framework_jwt.views import ObtainJSONWebToken

from wallet.repo import AccountDatabaseRepo, DrawQuotaRepo, ProductDataRepo, ReceiptRepo
import datetime

logger = logging.getLogger(__name__)


class ViewSignonWrapper(APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (AllowAny,)
    view_factory = None

    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        account_repo = AccountDatabaseRepo()
        body = account_repo.login(data["username"], data["password"])
        return Response(body, status=200)


class ViewAuthWrapper(APIView):
    permission_classes = (IsAuthenticated,)
    view_factory = None
    account_repo = AccountDatabaseRepo()

    def get(self, request, format=None, *args, **kwargs):
        params = request.user
        body = self.account_repo.get_user_profile(params)
        return Response(body, status=200)

    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        res = self.account_repo.update_profile(data)
        return Response(res, status=200)

    def delete(self, request, format=None, *args, **kwargs):
        res = self.account_repo.delete_user(**kwargs)
        return Response(res, status=200)


class UserWapper(APIView):
    permission_classes = (IsAdminUser,)
    view_factory = None

    def get(self, request, format=None, *args, **kwargs):
        account_repo = AccountDatabaseRepo()
        body = account_repo.get_all_users()
        return Response(body, status=200)


class QuotaWrapper(APIView):
    permission_classes = (IsAdminUser,)
    view_factory = None

    def get(self, request, format=None, *args, **kwargs):
        data = DrawQuotaRepo.get_quota_and_history(kwargs.get('username'))
        return Response(data, status=200)

    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        status, res = DrawQuotaRepo.update_quota_draw(data)
        return Response(res, status=status)


class ProductDataWrapper(APIView):
    permission_classes = (IsAdminUser,)
    view_factory = None

    def get(self, request, format=None, *args, **kwargs):
        data = ProductDataRepo.get_all_games_packages()
        return Response(data, status=200)

    def post(self, request, format=None, *args, **kwargs):
        data = request.data

        if data.get('type') == 'delete_package':
            status, res = ProductDataRepo.delete_package(data.get('data'))
            return Response(res, status=status)

        if data.get('type') == 'updatePackage':
            status, res = ProductDataRepo.update_packages(data['data'])
        else:
            status, res = DrawQuotaRepo.update_quota_draw(data)
        return Response(res, status=status)


class RecieptWrapper(APIView):
    permission_classes = (IsAdminUser,)
    view_factory = None

    def get(self, request, format=None, *args, **kwargs):
        data = ReceiptRepo.get_receipts(request.query_params)
        return Response(data, status=200)


class OrdersWrapper(APIView):
    permission_classes = (IsAdminUser,)
    view_factory = None

    def get(self, request, format=None, *args, **kwargs):
        data =  ReceiptRepo.get_orders(request.query_params)
        return Response(data, status=200)


class StorageWrapper(APIView):
    permission_classes = (IsAdminUser,)
    view_factory = None

    def get(self, request, format=None, *args, **kwargs):
        data = ReceiptRepo.get_storage(request.query_params)
        return Response(data, status=200)


class ImportExportWrapper(APIView):
    permission_classes = (IsAdminUser,)
    view_factory = None

    def get(self, request, format=None, *args, **kwargs):
        return ReceiptRepo.export_tokens(request.query_params)

    def post(self, request, format=None, *args, **kwargs):
        data = request.data
        code, res = ReceiptRepo.import_tokens(data['importedFile'])
        return Response(res, status=code)


class CustomObtainJSONWebToken(ObtainJSONWebToken):
    def post(self, request, *args, **kwargs):
        print("heloooooooooooo")
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.object.get('user') or request.user
            if not user:
                return Response({'code': -200, 'data': None, "message": "invalid login credentials",
                                 "serviceTime": datetime.datetime.now()})
            token = jwt_encode_handler(jwt_payload_handler(user))

            return Response({"code": 200, "message": "OK",
                             "token": token,
                             "serviceTime": datetime.datetime.now(),
                             "data": {"account": user.username,
                                      "authToken": token
                                      }})
        except Exception as ex:
            return Response({'code': -200, 'data': None, "message": "invalid login credentials",
                             "serviceTime": datetime.datetime.now()})
