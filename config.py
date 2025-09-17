import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    ROBOKASSA_MERCHANT_LOGIN = os.getenv("ROBOKASSA_MERCHANT_LOGIN", "demo")
    ROBOKASSA_PASSWORD1 = os.getenv("ROBOKASSA_PASSWORD1", "password1")
    ROBOKASSA_PASSWORD2 = os.getenv("ROBOKASSA_PASSWORD2", "password2")
    ROBOKASSA_TEST_MODE = os.getenv("ROBOKASSA_TEST_MODE", "1").lower() in ("1", "true", "yes")
