import logging

from rest_framework import serializers

from wallet.models import UserModel, ProductData

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ['username', 'raw_pass', 'is_active', 'is_superuser']


class ProductDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductData
        fields = ["description",
                  "gameName",
                  "packageName",
                  "price",
                  "productId",
                  "title",
                  "price_amount_micros",
                  "price_currency_code",
                  "skudetailstoken",
                  "type"]
