# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Classification(models.Model):
    sentence = models.CharField(max_length=200)
    label = models.CharField(max_length=50, blank=True, null=True)
    file = models.CharField(max_length=80)
    uuid = models.CharField(max_length=65, blank=True, null=True)
    last_change_time = models.DateTimeField(blank=True, null=True)
    ner = models.CharField(max_length=300, blank=True, null=True)
    tuple = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'classification'


class CompanyIdMap(models.Model):
    fake_id = models.IntegerField(primary_key=True)
    company_id = models.IntegerField()
    company = models.CharField(max_length=50, blank=True, null=True)
    dialog_counts = models.IntegerField(blank=True, null=True)
    industry = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'company_id_map'
        unique_together = (('fake_id', 'company_id'),)


class Cqa(models.Model):
    uuid = models.CharField(max_length=20)
    context = models.CharField(max_length=100, blank=True, null=True)
    question = models.CharField(max_length=100, blank=True, null=True)
    answer = models.CharField(max_length=200, blank=True, null=True)
    file = models.CharField(max_length=50)
    label = models.CharField(max_length=10, blank=True, null=True)
    last_change_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cqa'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class EntityRelationship(models.Model):
    entity_value_relationship = models.CharField(max_length=600, blank=True, null=True)
    dialog_id = models.PositiveIntegerField(blank=True, null=True)
    file = models.CharField(max_length=80, blank=True, null=True)
    last_change_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'entity_relationship'


class FileCheck(models.Model):
    check_file = models.CharField(max_length=60)
    gen_check_file = models.CharField(max_length=60)
    rate = models.FloatField(blank=True, null=True)
    check_date = models.DateTimeField(blank=True, null=True)
    is_pass = models.CharField(max_length=1, blank=True, null=True)
    pass_date = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'file_check'


class FileOrigin(models.Model):
    file = models.CharField(max_length=80, blank=True, null=True)
    origin = models.CharField(max_length=80, blank=True, null=True)
    last_change_date = models.DateTimeField(blank=True, null=True)
    upload_date = models.DateTimeField(blank=True, null=True)
    creater = models.CharField(max_length=4, blank=True, null=True)
    is_check = models.CharField(max_length=5, blank=True, null=True)
    is_pass = models.CharField(max_length=1, blank=True, null=True)
    submit_check_date = models.DateTimeField(blank=True, null=True)
    passed_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'file_origin'


class Graph(models.Model):
    dialog_id = models.PositiveIntegerField(blank=True, null=True)
    sentence_id = models.IntegerField(blank=True, null=True)
    role = models.CharField(max_length=6, blank=True, null=True)
    sentence = models.CharField(max_length=300, blank=True, null=True)
    file = models.CharField(max_length=80, blank=True, null=True)
    entity = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'graph'


class Marktool(models.Model):
    file = models.CharField(max_length=255, blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)
    context = models.CharField(max_length=255, blank=True, null=True)
    answer = models.CharField(max_length=255, blank=True, null=True)
    last_change_time = models.DateTimeField(blank=True, null=True)
    uuid = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'marktool'


class Multiclassification(models.Model):
    uuid = models.BigIntegerField(blank=True, null=True)
    sentence = models.TextField(blank=True, null=True)
    label = models.TextField(blank=True, null=True)
    file = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'multiclassification'


class ScrmLifeCode(models.Model):
    id = models.BigAutoField(primary_key=True)
    qrcode_type = models.IntegerField(blank=True, null=True)
    qrcode_name = models.CharField(max_length=255, blank=True, null=True)
    personids = models.CharField(max_length=2000, blank=True, null=True)
    really_personids = models.CharField(max_length=2000, blank=True, null=True)
    verification = models.IntegerField(blank=True, null=True)
    distribution_type = models.IntegerField(blank=True, null=True)
    distribution_value = models.IntegerField(blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    is_remind = models.IntegerField(blank=True, null=True)
    remind_users = models.CharField(max_length=2000, blank=True, null=True)
    labels = models.CharField(max_length=2000, blank=True, null=True)
    welcome_msg = models.CharField(max_length=500, blank=True, null=True)
    auto_send = models.IntegerField(blank=True, null=True)
    content_type = models.IntegerField(blank=True, null=True)
    content = models.CharField(max_length=1000, blank=True, null=True)
    qrcode_state = models.IntegerField(blank=True, null=True)
    error_msg = models.CharField(max_length=255, blank=True, null=True)
    last_scan_time = models.DateTimeField(blank=True, null=True)
    last_valid_date = models.DateTimeField(blank=True, null=True)
    qrcode_url = models.CharField(max_length=1000, blank=True, null=True)
    total_scan = models.BigIntegerField(blank=True, null=True)
    config_id = models.CharField(max_length=255, blank=True, null=True)
    wechat_url = models.CharField(max_length=1000, blank=True, null=True)
    create_id = models.BigIntegerField(blank=True, null=True)
    create_time = models.DateTimeField(blank=True, null=True)
    last_update_id = models.BigIntegerField(blank=True, null=True)
    last_update_time = models.DateTimeField(blank=True, null=True)
    waiter_id = models.CharField(max_length=255, blank=True, null=True)
    waiter_tips = models.CharField(max_length=1000, blank=True, null=True)
    is_permanent = models.IntegerField(blank=True, null=True)
    group_avatars = models.CharField(max_length=500, blank=True, null=True)
    bg_img_url = models.CharField(max_length=500, blank=True, null=True)
    logo_img_url = models.CharField(max_length=500, blank=True, null=True)
    qrcode_img_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'scrm_life_code'


class ScrmQrcodeGroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    lifecode_id = models.BigIntegerField(blank=True, null=True)
    group_id = models.CharField(max_length=255, blank=True, null=True)
    group_qrcode = models.CharField(max_length=2000, blank=True, null=True)
    valid_date = models.DateTimeField(blank=True, null=True)
    group_state = models.IntegerField(blank=True, null=True)
    qroup_index = models.IntegerField(blank=True, null=True)
    create_id = models.BigIntegerField(blank=True, null=True)
    create_time = models.DateTimeField(blank=True, null=True)
    last_update_id = models.BigIntegerField(blank=True, null=True)
    last_update_time = models.DateTimeField(blank=True, null=True)
    group_address = models.CharField(max_length=255, blank=True, null=True)
    group_province = models.CharField(max_length=255, blank=True, null=True)
    group_city = models.CharField(max_length=255, blank=True, null=True)
    group_areas = models.CharField(max_length=255, blank=True, null=True)
    group_qrcode_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'scrm_qrcode_group'


class ScrmRiskConfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    config_name = models.CharField(max_length=255, blank=True, null=True)
    config_value = models.CharField(max_length=500, blank=True, null=True)
    config_describe = models.CharField(max_length=500, blank=True, null=True)
    create_time = models.DateTimeField(blank=True, null=True)
    update_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'scrm_risk_config'


class ScrmRiskIgnore(models.Model):
    id = models.BigAutoField(primary_key=True)
    content = models.CharField(max_length=500, blank=True, null=True)
    create_time = models.DateTimeField(blank=True, null=True)
    update_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'scrm_risk_ignore'


class ToTest(models.Model):
    sentence = models.CharField(max_length=200)
    label = models.CharField(max_length=20, blank=True, null=True)
    file = models.CharField(max_length=40)
    uuid = models.CharField(max_length=65, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'to_test'


class TwoTuples(models.Model):
    sentence = models.CharField(max_length=200)
    label = models.CharField(max_length=50, blank=True, null=True)
    file = models.CharField(max_length=80)
    uuid = models.CharField(max_length=65)
    last_change_date = models.DateTimeField(blank=True, null=True)
    ner = models.CharField(max_length=300, blank=True, null=True)
    tuple = models.CharField(max_length=400, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'two_tuples'


class User(models.Model):
    username = models.CharField(primary_key=True, max_length=16)
    password = models.CharField(max_length=16)
    permission = models.IntegerField(blank=True, null=True)
    token = models.CharField(max_length=200, blank=True, null=True)
    zh_name = models.CharField(max_length=10, blank=True, null=True)
    ip = models.CharField(max_length=32, blank=True, null=True)
    last_change_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user'
