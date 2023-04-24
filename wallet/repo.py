import csv

from openpyxl.writer.excel import save_virtual_workbook
from collections import defaultdict
from datetime import datetime
from io import BytesIO, StringIO

import pandas as pd
import django_bulk_update.helper
from bulk_update.helper import bulk_update
from django.db import connection
from django.http import Http404, HttpResponse
from rest_framework_jwt.serializers import (jwt_encode_handler,
                                            jwt_payload_handler)

from wallet.models import UserModel, DrawQuota, Receipt, HistoryQuota, ProductData
from wallet.serializers import UserSerializer
from django.core.exceptions import ObjectDoesNotExist


class AccountDatabaseRepo(object):
    def login(self, email, password):
        try:
            user = UserModel.objects.get(username=email)
            if not user.is_active:
                raise Exception

            if user.check_password(password):
                try:
                    user.last_login = datetime.now()
                    user.save()
                    payload = jwt_payload_handler(user)
                    token = jwt_encode_handler(payload)
                    return {"token": token}
                except Exception as e:
                    raise e
        except KeyError:
            res = {"error": "Please enter the correct email address and password"}
            return {"res": res}

    def get_user_profile(self, params):
        try:
            if user := UserModel.objects.get(username=params.username):
                serializer = UserSerializer(user)
                return {"user": serializer.data}
        except Exception as e:
            raise Http404("User does not exist") from e

    def get_all_users(self):
        all_users = UserModel.objects.all()
        serializer = UserSerializer(all_users, many=True)
        return {"users": serializer.data}

    def update_profile(self, update_users):
        try:
            update_users_dict = {user['username']: user for user in update_users}
            self.update(update_users_dict)
            self.create(update_users_dict)
            return {"res": 'Updated successfully!'}
        except Exception as ex:
            return {"res": 'User does not exist'}

    def update(self, update_users_dict):
        if not update_users_dict:
            return
        users = UserModel.objects.filter(username__in=update_users_dict.keys())
        for user in users:
            user.raw_pass = update_users_dict[user.username]['raw_pass']
            if user.raw_pass:
                user.set_password(user.raw_pass)
            user.set_is_superuser(update_users_dict[user.username]['is_superuser'])
            del update_users_dict[user.username]
        bulk_update(users)

    def create(self, update_users_dict):
        if not update_users_dict:
            return
        new_users = []
        for username, data in update_users_dict.items():
            new_user = UserModel()
            new_user.username = username
            new_user.set_is_superuser(data['is_superuser'])
            new_user.set_password(data['raw_pass'])
            new_user.raw_pass = data['raw_pass']
            new_users.append(new_user)

        UserModel.objects.bulk_create(new_users)

    def delete_user(self, username: str):
        try:
            usernames = username.split(",")
            UserModel.objects.filter(username__in=usernames).delete()
            return {"res": 'Deleted successfully'}
        except Exception as ex:
            return {"res": 'User does not exist'}


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


class DrawQuotaRepo(object):

    @staticmethod
    def get_quota_and_history(username):
        """
        Get quota draw and history of user
        :param user:
        :return:
        """
        result = {}
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT product_data.game_name                                                     as game,
                       CONCAT(product_data.virtual_currency, ' - ', product_data.real_price)      as package,
                       CASE WHEN draw_quota.id IS NOT NULL THEN draw_quota.amount ELSE 0 END      as amount,
                       CASE WHEN draw_quota.id IS NOT NULL THEN draw_quota.amount_used ELSE 0 END as amount_used,
                       draw_quota.identify                                                        as identify,
                       draw_quota.game_id                                                         as game_id,
                       product_data.identify                                                      as product_data_game_identify,
                       product_data.game_id                                                       as product_data_game_id
                FROM product_data
                         LEFT JOIN draw_quota
                                   ON product_data.game_id = draw_quota.game_id AND product_data.identify = draw_quota.identify AND
                                      draw_quota.user_id = '{username}'
                                          """
            )
            result['quota'] = dictfetchall(cursor)
            game_and_package = tuple(
                (i['product_data_game_id'], i['product_data_game_identify']) for i in result['quota'])

            remain_amount = f"""select distinct(game_id, identify),
                                   Count(*) over (partition by game_id, identify) as remain_amount,
                                   game_id,
                                   identify
                                from receipt WHERE (game_id, identify) IN {game_and_package}
                                  and assigned_user is null
                                  and used = False"""

            remain_amount = cursor.execute(remain_amount)
            remain_amount = dictfetchall(cursor)

            for k in result['quota']:
                k['remain_amount'] = 0
                for i in remain_amount:
                    if k['product_data_game_id'] == i['game_id'] and k['product_data_game_identify'] == i['identify']:
                        k['remain_amount'] = i['remain_amount']

            cursor.execute(
                f"""
               SELECT product_data.game_name                                                as game,
                       CONCAT(product_data.virtual_currency, ' - ', product_data.real_price) as package,
                       history_quota.amount                                                  as amount,
                       history_quota.time_add                                                as time_add
                FROM history_quota
                         INNER JOIN product_data ON product_data.identify = history_quota.product_id
                    AND history_quota.user_id = '{username}'
                ORDER BY time_add DESC

                """
            )
            result['history'] = dictfetchall(cursor)

            return result

    @staticmethod
    def checkEnoughTokensRemain(params):
        return Receipt.objects.filter(game_id=params['game_id'],
                                      identify=params['identify'],
                                      assigned_user__isnull=True,
                                      used=False
                                      ).count()

    @staticmethod
    def update_quota_draw(params):
        try:
            remain_tokens = DrawQuotaRepo.checkEnoughTokensRemain(params)
            if remain_tokens < params['newAmount']:
                return 400, {'msg': f'Remain token not enough, remain: {remain_tokens}'}

            draw_quota = DrawQuota.objects.filter(game_id=params['game_id'],
                                                  identify=params['identify'],
                                                  user_id=params['userId'])
            if draw_quota.exists():
                draw_quota = draw_quota[0]
            else:
                # Create obj if not exist
                draw_quota = DrawQuota.objects.create(game_id=params['game_id'],
                                                      identify=params['identify'],
                                                      user_id=params['userId'],
                                                      amount=0,
                                                      amount_used=0)
            # reset to 0
            if params['newAmount'] < 0 and draw_quota.amount < abs(params['newAmount']):
                params['newAmount'] = draw_quota.amount

            draw_quota.amount += params['newAmount']
            draw_quota.save()
            DrawQuotaRepo.insert_history_draw_quota(params)
            DrawQuotaRepo.lock_tokens(params, 'revoke' if params['newAmount'] < 0 else 'assign')

            return 200, {'msg': 'Update amount successfully!'}

        except ObjectDoesNotExist:
            return 200, {"msg": 'DrawQuota does not exist'}


    @staticmethod
    def update_products(params):
        try:
            remain_tokens = DrawQuotaRepo.checkEnoughTokensRemain(params)
            if remain_tokens < params['newAmount']:
                return 400, {'msg': f'Remain token not enough, remain: {remain_tokens}'}

            draw_quota = DrawQuota.objects.get(game_id=params['game_id'],
                                               identify=params['identify'],
                                               user_id=params['userId'])
            # reset to 0
            if params['newAmount'] < 0 and draw_quota.amount < abs(params['newAmount']):
                params['newAmount'] = draw_quota.amount

            draw_quota.amount += params['newAmount']
            draw_quota.save()
            DrawQuotaRepo.insert_history_draw_quota(params)
            DrawQuotaRepo.lock_tokens(params, 'revoke' if params['newAmount'] < 0 else 'assign')

            return 200, {'msg': 'Update amount successfully!'}
        except ObjectDoesNotExist:
            return 200, {"msg": 'DrawQuota does not exist'}

    @staticmethod
    def lock_tokens(params, action):
        receipts = []
        if action == 'revoke':
            receipts = Receipt.objects.filter(game_id=params['game_id'],
                                              identify=params['identify'],
                                              assigned_user=params['userId'],
                                              used=False).order_by('-id')[:abs(params['newAmount'])]
            for receipt in receipts:
                receipt.assigned_user = None

        elif action == 'assign':
            receipts = Receipt.objects.filter(game_id=params['game_id'],
                                              identify=params['identify'],
                                              assigned_user__isnull=True,
                                              used=False).order_by('-id')[:abs(params['newAmount'])]
            for receipt in receipts:
                receipt.assigned_user = params['userId']

        django_bulk_update.helper.bulk_update(receipts)


    @staticmethod
    def insert_history_draw_quota(params):
        HistoryQuota.objects.create(
            game_id=params['game_id'],
            product_id=params['identify'],
            user_id=params['userId'],
            amount=params['newAmount'],
        )


class ProductDataRepo:

    @staticmethod
    def get_all_games_packages():
        all_games = ProductData.objects.all()
        result = defaultdict(dict)
        for game in all_games:
            result[game.game_id]['game_name'] = game.game_name
            if not result[game.game_id].get('packages'):
                result[game.game_id]['packages'] = []

            result[game.game_id]['packages'].append(
                {'text': f'{game.virtual_currency} - {game.real_price}',
                 'value': game.identify,
                 'virtual_currency': game.virtual_currency,
                 'real_price': game.real_price,
                 }
            )
        return {'games': result}

    @staticmethod
    def update_packages(data):
        try:
            all_games = ProductData.objects.all()
            for game in all_games:
                current_update = None
                for i in data:
                    if i['game_id'] == game.game_id and i['package_id'] == game.identify:
                        current_update = i
                if current_update:
                    game.game_name = current_update['game_name']
                    game.virtual_currency = current_update['package_name']
                    game.real_price = current_update['real_price']
            django_bulk_update.helper.bulk_update(all_games)
        except Exception as ex:
            return 400, {'msg': ex}
        return 200, {'msg': 'Update success fully!'}

    @staticmethod
    def delete_package(data):
        try:
            print('about to delete')
            ProductData.objects.filter(identify=data['identify'], game_id=data['game_id']).delete()
            Receipt.objects.filter(identify=data['identify'], game_id=data['game_id']).delete()
            DrawQuota.objects.filter(identify=data['identify'], game_id=data['game_id']).delete()
        except Exception as ex:
            print('Exception----')
            import traceback
            traceback.print_exc()
            return 400, {'msg': ex}
        return 200, {'msg': 'Deleted success fully!'}


class ReceiptRepo:

    @staticmethod
    def get_receipts(params):
        if params['gameId'] == 'All':
            query = f"""
                         select product_data.game_name,
                               CONCAT(product_data.virtual_currency, ' - ', product_data.real_price) as name,
                               count(receipt.id)                                                     as amount
                        from receipt
                                 join product_data on receipt.identify = product_data.identify
                        where receipt.user_id = '{params['userId']}'

                          """
        else:
            query = f"""
                         select product_data.game_name,
                               CONCAT(product_data.virtual_currency, ' - ', product_data.real_price) as name,
                               count(receipt.id)                                                     as amount
                        from receipt
                                 join product_data on receipt.identify = product_data.identify
                        where receipt.user_id = '{params['userId']}' and product_data.game_id = '{params['gameId']}'
                          """
            if params.get('identify') and params.get('identify') != 'All':
                query += f" and product_data.identify = '{params['identify']}'"
            if params.get('fromDate') and params.get('toDate'):
                query += f" and receipt.create_time between '{params['fromDate']}' and '{params['toDate']}'"

        query += ' group by receipt.identify, product_data.game_name, product_data.virtual_currency, ' \
                 'product_data.real_price '

        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

        return {'data': result}

    @staticmethod
    def get_orders(params):
        if params['gameId'] == 'All':
            query = f"""
                SELECT product_data.game_name,
                       CONCAT(product_data.virtual_currency, ' - ', product_data.real_price) as package,
                       count(order_info.id)                                                  as amount
                FROM order_info join receipt on receipt.id = order_info.receipt_id
                         join product_data on receipt.identify = product_data.identify
                WHERE receipt.user_id = '{params['userId']}'
                
                      """
        else:
            query = f"""
                SELECT product_data.game_name,
                       CONCAT(product_data.virtual_currency, ' - ', product_data.real_price) as package,
                       count(order_info.id)                                                  as amount
                FROM order_info join receipt on receipt.id = order_info.receipt_id
                         join product_data on receipt.identify = product_data.identify
                where receipt.user_id = '{params['userId']}' and product_data.game_id = '{params['gameId']}'
                      """
            if params.get('identify') and params.get('identify') != 'All':
                query += f" and product_data.identify = '{params['identify']}'"
            if params.get('fromDate') and params.get('toDate'):
                query += f" and order_info.create_time between '{params['fromDate']}' and '{params['toDate']}'"
        query += ' group by receipt.identify, product_data.game_name, product_data.virtual_currency, ' \
                 'product_data.real_price '

        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

        return {'data': result}

    @staticmethod
    def get_storage(params):
        if params['gameId'] == 'All':
            query = f"""
                SELECT product_data.game_name,
                       CONCAT(product_data.virtual_currency, ' - ', product_data.real_price) as package,
                       count(*)                                                              as total,
                       count(case when receipt.assigned_user is not null then 1 end)         as assigned,
                       count(case when receipt.used = False then 1 end)                      as not_used,
                       count(case when receipt.used = True then 1 end)                       as used
                FROM product_data
                         join receipt on receipt.identify = product_data.identify
                      """
        else:
            query = f"""
                SELECT product_data.game_name,
                       CONCAT(product_data.virtual_currency, ' - ', product_data.real_price) as package,
                       count(*)                                                              as total,
                       count(case when receipt.assigned_user is not null then 1 end)         as assigned,
                       count(case when receipt.used = False then 1 end)                      as not_used,
                       count(case when receipt.used = True then 1 end)                       as used
                FROM product_data
                         join receipt on receipt.identify = product_data.identify
                where product_data.game_id = '{params['gameId']}'
                      """
            if params.get('identify') and params.get('identify') != 'All':
                query += f" and product_data.identify = '{params['identify']}'"

        query += ' group by receipt.identify, product_data.game_name, product_data.virtual_currency, ' \
                 'product_data.real_price '

        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

        return {'data': result}

    @staticmethod
    def export_tokens(params):
        export_data = Receipt.objects.filter(game_id=params['gameId'],
                                             identify=params['identify'],
                                             assigned_user__isnull=True
                                             )
        if export_data.count() < int(params['amount']):
            return HttpResponse(status=400, content=f'Amount remain is: {export_data.count()}, not enough!')

        query = f"""
            SELECT id, identify, user_id,game_id, user_id,token, signature, order_id, create_time
            FROM receipt
            where game_id = '{params['gameId']}' and identify='{params['identify']}' and assigned_user is null limit {params['amount']} """

        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)
            response = ReceiptRepo.create_response_with_csv_format(result)
            Receipt.objects.filter(id__in=[i['id'] for i in result]).delete()
        return response

    @staticmethod
    def create_response_with_csv_format(result):
        response = HttpResponse(
            content_type='text/csv',
        )
        response['Content-Disposition'] = 'attachment; filename="myfile.csv"'
        response['status'] = 200
        writer = csv.writer(response)
        writer.writerow(
            ['identify', 'user_id', 'game_id', 'user_id', 'token', 'signature', 'order_id', 'create_time'])
        for i in result:
            writer.writerow([
                i['identify'], i['user_id'], i['game_id'], i['user_id'], i['token'], i['signature'], i['order_id'],
                i['create_time']])
        return response

    @staticmethod
    def import_tokens(file):
        file = file.read().decode('utf-8')
        reader = csv.DictReader(StringIO(file))
        tokens = list(reader)
        if tokens:
            accepted_fields = ['identify', 'user_id', 'game_id', 'user_id', 'token', 'signature', 'order_id',
                               'create_time']
            if set(tokens[0].keys()) - set(accepted_fields) != set():
                return 400, {'msg': f'Accept these columns only: {[i + "," for i in accepted_fields]}'}

        tokens = [Receipt(**line, **{'used': False}) for line in tokens]
        Receipt.objects.bulk_create(tokens)
        return 200, {'msg': 'Imported successfully'}


class BasePermission:

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return True
