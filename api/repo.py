from django.db import transaction, IntegrityError

from wallet.models import ProductData, Receipt, OrderInfo
from wallet.repo import DrawQuotaRepo
from datetime import datetime


def build_common_response(data='OK', message='OK'):
    now = datetime.now()
    formatted_date = now.strftime('%a %b %d, %Y %H:%M')

    return {
        'code': 200,
        'data': data,
        'message': message,
        'serviceTime': formatted_date
    }


def build_failed_response(status_code, message):
    result = build_common_response()
    result['code'] = status_code
    result['message'] = message

    return result


class SkuRepo:
    insert_params = [
        'description', 'gameName', 'packageName',
        'price', 'price_amount_micros', 'price_currency_code',
        'productId', 'skuDetailsToken', 'title', 'type'
    ]

    @staticmethod
    def is_params_valid(params):
        return set(params.keys()) - set(SkuRepo.insert_params) != set()

    @staticmethod
    def get_sku(params):
        if not params.get('packageName'):
            return 400, build_failed_response(message='Invalid Getsku params')
        result = ProductData.objects.filter(game_id=params.get('packageName'))
        result = [
            {'description': i.description,
             'gameName': i.game_name,
             'packageName': i.game_id,
             'price': i.real_price,
             'productId': i.identify,
             'title': i.virtual_currency,
             'price_amount_micros': i.price_amount_micros,
             'price_currency_code': i.price_currency_code,
             'skuDetailsToken': i.skudetailstoken,
             'type': i.type,
             } for i in result
        ]
        print('here--------')
        print(build_common_response(result, 'OK'))
        return 200, build_common_response(result, 'OK')

    @staticmethod
    def push_sku(params):
        if SkuRepo.is_params_valid(params):
            return 400, {'msg': 'Param posted is wrong'}

        package_name, product_id = params['packageName'], params['productId']
        isExisted = ProductData.objects.filter(game_id=package_name, identify=product_id).count() > 0

        if isExisted:
            return 200, {'msg': 'Product existed!'}

        try:
            insert_obj = {
                "identify": params['productId'],
                "real_price": params['price'],
                "virtual_currency": params['title'],
                "game_id": params['packageName'],
                "game_name": params['gameName'],
                "price_amount_micros": params['price_amount_micros'],
                "price_currency_code": params['price_currency_code'],
                "skudetailstoken": params['skuDetailsToken'],
                "type": params['type'],
                "description": params['description'],
            }

            ProductData.objects.create(
                **insert_obj
            )
            return 200, build_common_response()
        except Exception as ex:
            return 400, build_failed_response(-200, f'Push failed due to internal error {str(ex)}')


class TokenRepo:
    @staticmethod
    def get_token(params, user):
        if not params.get('packageName') and params.get('productId'):
            return 400, {'msg': ' invalid gettoken request params'}

        tokens = Receipt.objects.filter(game_id=params['packageName'],
                                        identify=params['productId'],
                                        assigned_user=user.username,
                                        used=False)
        if tokens.count() <= 0:
            return 400, {'msg': 'Not enough token'}
        token = tokens.first()

        try:
            with transaction.atomic():
                order = {
                    "receipt_id": token.id,
                    "user_id": user.username,
                    "device_number": '123',
                    "status": '3'

                }
                OrderInfo.objects.create(**order)
                token.used = True
                token.save()
                DrawQuotaRepo.consumeToken(params['packageName'], params['productId'], user.username)
        except Exception as ex:
            return 400, build_failed_response(f'Internal error{ex})')
        return 200, build_common_response([
            {"mOriginalJson": token.token,
             "mSignature": token.signature,
             "orderId": token.order_id,
             "packageName": token.game_id,
             "sku": token.identify,
             }
        ])

    @staticmethod
    def push_token(params, user):

        if {'packageName', 'sku', 'mOriginalJson', 'mSignature', 'orderId'} - params.keys() != set():
            return 400, {'message': 'invalid pushtoken params'}

        if Receipt.objects.filter(
                game_id=params['packageName'], identify=params['sku'], order_id=params["orderId"]
        ).exists():
            return 400, {'message': 'token already exist'}

        try:
            Receipt.objects.create(
                game_id=params['packageName'],
                identify=params['sku'],
                user_id=user.username,
                token=params['mOriginalJson'],
                signature=params['mSignature'],
                order_id=params['orderId'],
                used=False,
                assigned_user=None
            )
            return 200, build_common_response()
        except Exception as ex:
            return 400, build_failed_response(str(ex))


class ProductRepo:
    @staticmethod
    def get_export(params):
        if not (params.get('packageName') and params.get('productId')):
            return 400, {'msg': 'Invalid params'}
        data = ProductData.objects.filter(game_id=params.get('packageName'), identify=params.get('productId'))

        return 200, build_common_response([
            {
                'count': 1,
                "game_name": i.game_name,
                "packageName": i.game_id,
                "price": i.real_price,
                "productId": i.identify,
                "title": i.virtual_currency
            } for i in data
        ])
