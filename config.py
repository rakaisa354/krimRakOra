import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SHEETS_ID   = os.getenv("GOOGLE_SHEETS_ID")
CLAUDE_API_KEY     = os.getenv("CLAUDE_API_KEY")
FX_API_KEY         = os.getenv("FX_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_CURRENCY      = os.getenv("BASE_CURRENCY", "INR")
SALARY_DAY         = int(os.getenv("SALARY_DAY", "1"))
