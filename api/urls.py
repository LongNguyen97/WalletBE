from django.urls import path

from api.views import SkuWrapper, TokenWrapper, ExportWrapper

urlpatterns = [
    path(
        "getsku",
        SkuWrapper.as_view(),
        name="sku",
    ),
    path(
        "pushsku",
        SkuWrapper.as_view(),
        name="sku",
    ),
    path(
        "push-token",
        TokenWrapper.as_view(),
        name="token",
    ),
    path(
        "get-token",
        TokenWrapper.as_view(),
        name="token",
    ),
    path(
        "getexport",
        ExportWrapper.as_view(),
        name="export",
    ),

]
