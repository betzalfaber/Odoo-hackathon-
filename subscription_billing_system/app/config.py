import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "subscription_billing.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

SECRET_KEY = os.getenv("SECRET_KEY", "subscription_billing_secret_key_2026_super_secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours
