from django.urls import path

from api.views import PushSkuWrapper, PushTokenWrapper, GetTokenWrapper, ExportWrapper, GetSkuWrapper

urlpatterns = [
    path(
        "getsku",
        GetSkuWrapper.as_view(),
        name="sku",
    ),
    path(
        "pushsku",
        PushSkuWrapper.as_view(),
        name="sku",
    ),
    path(
        "push-token",
        PushTokenWrapper.as_view(),
        name="token",
    ),
    path(
        "get-token",
        GetTokenWrapper.as_view(),
        name="token",
    ),
    path(
        "getexport",
        ExportWrapper.as_view(),
        name="export",
    ),

]
