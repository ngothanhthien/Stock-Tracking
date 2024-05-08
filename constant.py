import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = 'db.json'
DELAY = 0.5
TIME_OUT = 5
VP_USERNAME = os.getenv('VP_USERNAME')
VP_PASSWORD = os.getenv('VP_PASSWORD')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_TEST_CHANNEL_ID = os.getenv('DISCORD_TEST_CHANNEL_ID')
BASE_URL = 'https://external.vpbanks.com.vn'
API_URL = {
    'price_chart': "/invest/api/stock/getPriceChartLine?symbol={code}&chartType={type}",
    'realtime_price': "/invest/api/getPriceByList/5min?symbolList={code}",
    'login': "/auth/token",
}
REQUIRED_AUTH = {
    'watch_list': '/flex/userdata/watchlists',
    'own_list': '/flex/inq/accounts/{account_id}/securitiesPortfolio',
    'account_list': '/flex/accountsAll',
}
CHART_TYPE = {
    '1W': '1W',
    '3M': '3M',
    '1Y': '1Y',
}


def get_url(name: str, auth=False) -> str:
    if auth:
        path = REQUIRED_AUTH.get(name)
    else:
        path = API_URL.get(name)

    if not path:
        raise ValueError("Invalid API name")

    return f"{BASE_URL}{path}"
