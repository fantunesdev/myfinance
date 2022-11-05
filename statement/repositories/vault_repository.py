import os

import hvac


def export_mysql_credentials():
    client = hvac.Client(url=os.environ['URL'])
    os.environ['MYSQL_USER'] = client.kv.v1.read_secret('mysql/user')['data']['user']
    os.environ['MYSQL_PASSWORD'] = client.kv.v1.read_secret('mysql/password')['data']['password']


def export_postgre_credentials():
    client = hvac.Client(url=os.environ['URL'])
    os.environ['POSTGRESQL_USER'] = client.kv.v1.read_secret('postgresql/user')['data']['user']
    os.environ['POSTGRESQL_PASSWORD'] = client.kv.v1.read_secret('postgresql/password')['data']['password']
