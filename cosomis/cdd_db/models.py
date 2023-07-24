import secrets
import time
from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.db import models
from django.utils.translation import gettext_lazy as _

from no_sql_client import NoSQLClient


class Facilitator(models.Model):
    no_sql_user = models.CharField(max_length=150, unique=True)
    no_sql_pass = models.CharField(max_length=128)
    no_sql_db_name = models.CharField(max_length=150, unique=True)
    username = models.CharField(max_length=150, unique=True, verbose_name=_('username'))
    password = models.CharField(max_length=128, verbose_name=_('password'))
    code = models.CharField(max_length=6, unique=True, verbose_name=_('code'))
    active = models.BooleanField(default=False, verbose_name=_('active'))
    develop_mode = models.BooleanField(default=False, verbose_name=_('test mode'))
    training_mode = models.BooleanField(default=False, verbose_name=_('test mode'))

    name = models.CharField(max_length=200, null=True, blank=True, verbose_name=_('name'))
    email = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('email'))
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name=_('phone'))
    sex = models.CharField(max_length=5, null=True, blank=True, verbose_name=_('sex'))
    total_tasks = models.IntegerField(default=0)
    total_tasks_completed = models.IntegerField(default=0)
    last_activity = models.DateTimeField(blank=True, null=True)

    __current_password = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__current_password = self.password

    def __str__(self):
        return self.username

    def set_no_sql_user(self):
        now = str(int(time.time()))

        # Added to avoid repeating the same value for no_sql_user when bulk creating facilitators
        while Facilitator.objects.filter(no_sql_user=now).exists():
            now = str(int(time.time()))

        self.no_sql_user = now

    def hash_password(self, *args, **kwargs):
        self.password = make_password(self.password, salt=None, hasher='default')
        return super().save(*args, **kwargs)

    def create_without_no_sql_db(self, *args, **kwargs):

        if not self.code:
            self.code = self.get_code(self.no_sql_user)

        if not self.password:
            self.password = f'ChangeItNow{self.code}'

        self.password = make_password(self.password, salt=None, hasher='default')

        return super().save(*args, **kwargs)

    def create_with_no_sql_db(self, *args, **kwargs):

        if not self.id:
            self.set_no_sql_user()

            no_sql_pass_length = 13
            self.no_sql_pass = secrets.token_urlsafe(no_sql_pass_length)

            if not self.code:
                self.code = self.get_code(self.no_sql_user)

            nsc = NoSQLClient()
            nsc.create_user(self.no_sql_user, self.no_sql_pass)
            facilitator_db = nsc.get_db(self.no_sql_db_name)
            nsc.add_member_to_database(facilitator_db, self.no_sql_user)

        if self.password and self.password != self.__current_password:
            self.password = make_password(self.password, salt=None, hasher='default')

        return super().save(*args, **kwargs)

    def create_with_manually_assign_database(self, *args, **kwargs):

        if not self.id:
            self.set_no_sql_user()

            if not self.code:
                self.code = self.get_code(self.no_sql_user)

            if not self.password:
                self.password = f'ChangeItNow{self.code}'
            self.password = make_password(self.password, salt=None, hasher='default')

            nsc = NoSQLClient()
            nsc.create_user(self.no_sql_user, self.no_sql_pass)
            facilitator_db = nsc.get_db(self.no_sql_db_name)
            nsc.add_member_to_database(facilitator_db, self.no_sql_user)

        if self.password and self.password != self.__current_password:
            self.password = make_password(self.password, salt=None, hasher='default')

        return super().save(*args, **kwargs)

    @staticmethod
    def get_code(seed):
        import zlib
        return str(zlib.adler32(str(seed).encode('utf-8')))[:6]

    def get_name(self):
        try:
            nsc = NoSQLClient()
            facilitator_database = nsc.get_db(self.no_sql_db_name)
            return facilitator_database.get_query_result(
                {"type": "facilitator"}
            )[:][0]['name']
        except Exception as e:
            return None

    def get_name_with_sex(self):
        try:
            nsc = NoSQLClient()
            facilitator_doc = nsc.get_db(self.no_sql_db_name).get_query_result(
                {"type": "facilitator"}
            )[:][0]
            return f"{facilitator_doc['sex']} {facilitator_doc['name']}" if facilitator_doc.get('sex') else \
            facilitator_doc['name']
        except Exception as e:
            return None

    def get_email(self):
        try:
            nsc = NoSQLClient()
            facilitator_database = nsc.get_db(self.no_sql_db_name)
            return facilitator_database.get_query_result(
                {"type": "facilitator"}
            )[:][0]['email']
        except Exception as e:
            return None

    def get_type(self):
        if self.develop_mode and self.training_mode:
            return "develop-training"
        elif self.develop_mode:
            return "develop"
        elif self.training_mode:
            return "training"
        else:
            return "deploy"

    # def get_all_infos(self):
    #     nsc = NoSQLClient()
    #     facilitator_db = nsc.get_db(self.no_sql_db_name)
    #     docs = facilitator_db.all_docs(include_docs=True)['rows']
    #     name = None
    #     email = None
    #     phone = None
    #     name_with_sex = None
    #     cvds = []
    #
    #     total_tasks_completed = 0
    #     total_tasks_uncompleted = 0
    #     total_tasks = 0
    #     last_activity_date = "0000-00-00 00:00:00"
    #
    #     for doc in docs:
    #         _ = doc.get('doc')
    #         if _.get('type') == "facilitator":
    #             name = _["name"]
    #             email = _["email"]
    #             phone = _["phone"]
    #             name_with_sex = f"{_['sex']} {_['name']}" if _.get('sex') else _['name']
    #             cvds = get_cvds(_)
    #             break
    #
    #     for doc in docs:
    #         _ = doc.get('doc')
    #         if _.get('type') == "task":
    #             last_updated = datetime_complet_str(_.get('last_updated'))
    #             if last_updated and last_activity_date < last_updated:
    #                 last_activity_date = last_updated
    #
    #             for administrative_level_cvd in cvds:
    #                 village = administrative_level_cvd['village']
    #                 if village and str(village.get("id")) == str(_["administrative_level_id"]):
    #                     if _.get("completed"):
    #                         total_tasks_completed += 1
    #                     else:
    #                         total_tasks_uncompleted += 1
    #                     total_tasks += 1
    #
    #     percent = float("%.2f" % (((total_tasks_completed / total_tasks) * 100) if total_tasks else 0))
    #
    #     if last_activity_date == "0000-00-00 00:00:00":
    #         last_activity_date = None
    #     else:
    #         last_activity_date = datetime.strptime(last_activity_date, '%Y-%m-%d %H:%M:%S')
    #
    #     return {
    #         "name_with_sex": name_with_sex, "username": self.username, "tel": phone,
    #         'last_activity_date': last_activity_date, "percent": percent
    #     }

    class Meta:
        managed = False
        verbose_name = _('Facilitator')
        verbose_name_plural = _('Facilitators')
        db_table = 'authentication_facilitator'
