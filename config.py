# db
# config.py

import os

SQLALCHEMY_DATABASE_URI = os.environ.get('postgresql://kdc_db_user:QHCInmgZmUNHNhGKml7nwnAl4TyI6Njo@dpg-d02j86pr0fns73fhis8g-a.oregon-postgres.render.com/kdc_db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

