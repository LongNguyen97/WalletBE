"""wallet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token

from api.views import PushSkuWrapper, PushTokenWrapper, ExportWrapper, GetSkuWrapper, GetTokenWrapper
from wallet.views import ViewSignonWrapper, ViewAuthWrapper, UserWapper, QuotaWrapper, ProductDataWrapper, \
    RecieptWrapper, OrdersWrapper, StorageWrapper, ImportExportWrapper, CustomObtainJSONWebToken

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('api/', include('api.urls')),
    path(
        "login/",
        ViewSignonWrapper.as_view(),
        name="account-login",
    ),
    path(
        "profile/",
        ViewAuthWrapper.as_view(),
        name="account-profile",
    ),
    path(
        "profile/delete/<str:username>",
        ViewAuthWrapper.as_view(),
        name="account-profile",
    ),
    path(
        "profile/delete/<str:username>",
        ViewAuthWrapper.as_view(),
        name="account-profile",
    ),
    path(
        "quota/get-quota-and-history/<str:username>",
        QuotaWrapper.as_view(),
        name="get-quota-and-history",
    ),
    path(
        "quota/update-amount",
        QuotaWrapper.as_view(),
        name="update-amount",
    ),

    path(
        "all-games-packages/",
        ProductDataWrapper.as_view(),
        name="all-games-packages",
    ),
    path(
        "get-receipts/",
        RecieptWrapper.as_view(),
        name="get-receipts",
    ),
    path(
        "get-orders/",
        OrdersWrapper.as_view(),
        name="get-orders",
    ),
    path(
        "get-storage/",
        StorageWrapper.as_view(),
        name="get-storage",
    ),
    path(
        "export-import/",
        ImportExportWrapper.as_view(),
        name="export-import",
    ),

    path("token/refresh", refresh_jwt_token),
    path("token/", obtain_jwt_token),

    url(r'^api-token-auth/', CustomObtainJSONWebToken.as_view()),
    path(
        "all_users/",
        UserWapper.as_view(),
        name="account-profile",
    ),
    path(
        "backend_api/getsku",
        GetSkuWrapper.as_view(),
        name="sku",
    ),
    path(
        "backend_api/pushsku",
        PushSkuWrapper.as_view(),
        name="sku",
    ),
    path(
        "backend_api/push-token",
        PushTokenWrapper.as_view(),
        name="token",
    ),
    path(
        "backend_api/get-token",
        GetTokenWrapper.as_view(),
        name="token",
    ),
    path(
        "backend_api/getexport",
        ExportWrapper.as_view(),
        name="export",
    ),

]
