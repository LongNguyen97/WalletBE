import datetime

import django
from django.contrib.auth.models import AbstractUser
from django.db import models


# from django.contrib.auth.models import User


class UserModel(AbstractUser):
    raw_pass = models.TextField(blank=True)

    class Meta:
        db_table = "users"

    def set_is_superuser(self, val):
        self.is_superuser = val in [True, 'true', 'Admin']
        self.is_staff = val in [True, 'true', 'Admin']


class DrawQuota(models.Model):
    user_id = models.CharField(max_length=128)
    identify = models.CharField(max_length=128)
    game_id = models.CharField(max_length=128)
    amount = models.IntegerField()
    amount_used = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'draw_quota'


class HistoryQuota(models.Model):
    user_id = models.CharField(max_length=64)
    product_id = models.CharField(max_length=64)
    game_id = models.CharField(max_length=128)
    amount = models.IntegerField()
    time_add = models.DateTimeField(default=django.utils.timezone.now)
    class Meta:
        managed = False
        db_table = 'history_quota'


class OrderInfo(models.Model):
    receipt_id = models.IntegerField()
    user_id = models.CharField(max_length=128)
    device_number = models.CharField(max_length=64)
    time = models.DateTimeField()
    status = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'order_info'


class ProductData(models.Model):
    identify = models.CharField(max_length=200)
    real_price = models.CharField(max_length=12)
    virtual_currency = models.CharField(max_length=64)
    game_id = models.CharField(max_length=128)
    game_name = models.CharField(max_length=128)
    price_amount_micros = models.BigIntegerField()
    price_currency_code = models.CharField(max_length=16)
    skudetailstoken = models.TextField()
    type = models.CharField(max_length=16)
    description = models.CharField(max_length=64)

    class Meta:
        managed = False
        db_table = 'product_data'


class Receipt(models.Model):
    game_id = models.CharField(max_length=64)
    identify = models.CharField(max_length=64)
    user_id = models.CharField(max_length=64)
    assigned_user = models.CharField(max_length=128)
    token = models.TextField()
    signature = models.TextField()
    order_id = models.CharField(max_length=64)
    used = models.BooleanField()
    create_time = models.DateTimeField(default=django.utils.timezone.now)

    class Meta:
        managed = False
        db_table = 'receipt'
