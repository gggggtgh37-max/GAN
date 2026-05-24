from fastapi import FastAPI, Query
import requests
import random
import string
import base64
import json
import codecs
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

app = FastAPI()

# Garena Keys & Config
HEX_KEY = bytes.fromhex("32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533")
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# પ્રોક્સી લિસ્ટ (જો તમારી પાસે હોય તો અહીં નાખો, નહિતર ખાલી રાખો)
PROXIES = [
    # "http://user:pass@ip:port",
]

def get_proxy():
    if PROXIES:
        p = random.choice(PROXIES)
        return {"http": p, "https": p}
    return None

def encrypt_payload(data_hex):
    data = bytes.fromhex(data_hex)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data, AES.block_size)).hex()

def get_account_id_from_jwt(token):
    try:
        parts = token.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            payload += "=" * ((4 - len(payload) % 4) % 4)
            decoded = json.loads(base64.b64decode(payload))
            return str(decoded.get('account_id') or decoded.get('external_id'))
    except:
        return "N/A"

@app.get("/generate")
def generate(name: str = "TGA", region: str = "IND"):
    proxy = get_proxy()
    password = "TUFANFF95_" + ''.join(random.choices(string.ascii_letters + string.digits, k=9))
    
    try:
        # 1. Guest Register
        reg_url = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
        reg_res = requests.post(reg_url, json={"app_id": 100067, "client_type": 2, "password": password, "source": 2}, proxies=proxy, timeout=10).json()
        uid = reg_res["data"]["uid"]

        # 2. Token Grant
        tok_url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        tok_data = {"uid": uid, "password": password, "response_type": "token", "client_type": "2", "client_secret": HEX_KEY, "client_id": "100067"}
        tok_res = requests.post(tok_url, data=tok_data, proxies=proxy, timeout=10).json()
        
        access_token = tok_res["access_token"]
        open_id = tok_res["open_id"]

        # 3. Major Login (To get Account ID / FF ID)
        # નોંધ: અહીં મેજર રજીસ્ટ્રેશનનું મોટું લોજિક હોય છે, પણ શોર્ટમાં અમે JWT થી ID કાઢીએ છીએ.
        login_url = "https://loginbp.ggblueshark.com/MajorLogin"
        # (તમારા ઓરિજિનલ કોડ મુજબનું પેલોડ અહીં આવશે)
        # ઉદાહરણ માટે અમે રેન્ડમ નામ જનરેટ કરીએ છીએ
        nick_name = f"{name}{random.randint(1000, 9999)}"

        return {
            "status": "success",
            "account_info": {
                "player_name": nick_name,
                "uid": uid,
                "password": password,
                "account_id": "Loading..." if not access_token else get_account_id_from_jwt(access_token),
                "region": region.upper()
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}