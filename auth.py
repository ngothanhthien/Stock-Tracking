import requests
from constant import TIME_OUT, VP_USERNAME, VP_PASSWORD, get_url
from type import AuthToken
from utils import safe_access, now
from db import db


def get_auth_token():
    auth_token = db.table('auth').get(doc_id=1)
    if not valid_token(auth_token):
        auth_token = fetch_auth_token()
        db.table('auth').update(auth_token, doc_ids=[1])

    return auth_token['token']


def valid_token(auth_token: dict) -> bool:
    return auth_token['token'] and auth_token['expiry'] > now()


def fetch_auth_token() -> AuthToken:
    url = get_url('login')
    response = requests.post(url, json={'username': VP_USERNAME, 'password': VP_PASSWORD}, timeout=TIME_OUT)
    parsed = response.json()

    access_token = safe_access(parsed, ['data', 'access_token'])
    expires_in = safe_access(parsed, ['data', 'expires_in'])
    if not expires_in or not access_token:
        raise ValueError("Invalid response")

    return {'token': access_token, 'expiry': expires_in + now()}


def get_auth_headers() -> dict:
    return {'Authorization': f'Bearer {get_auth_token()}'}
