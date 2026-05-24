from flask import Flask, request, jsonify
import requests
import random
import string
import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

app = Flask(__name__)

# --- GARENA CONFIG ---
HEX_KEY = bytes.fromhex("32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533")
REGION_LANG = {"ME":"ar","IND":"hi","ID":"id","VN":"vi","TH":"th","BD":"bn","PK":"ur","TW":"zh","CIS":"ru","SAC":"es","BR":"pt"}

# --- HELPERS ---
def encode_varint(n):
    result = []
    while True:
        byte = n & 0x7F
        n >>= 7
        if n: byte |= 0x80
        result.append(byte)
        if not n: break
    return bytes(result)

def create_proto_field(field_num, value):
    header = (field_num << 3) | (2 if isinstance(value, (str, bytes)) else 0)
    if isinstance(value, int): return encode_varint(header) + encode_varint(value)
    encoded_val = value.encode() if isinstance(value, str) else value
    return encode_varint(header) + encode_varint(len(encoded_val)) + encoded_val

def build_proto(fields):
    return b''.join(create_proto_field(k, v) for k, v in fields.items())

def aes_encrypt(hex_data):
    data = bytes.fromhex(hex_data)
    aes_key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

def get_account_id_from_jwt(jwt_token):
    try:
        parts = jwt_token.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            # Base64 padding fix
            padding = 4 - (len(payload) % 4)
            if padding != 4: payload += "=" * padding
            decoded = json.loads(base64.b64decode(payload).decode('utf-8'))
            return str(decoded.get('account_id') or decoded.get('external_id') or "N/A")
    except:
        return "N/A"
    return "N/A"

# --- API ROUTES ---
@app.route('/')
def home():
    return "TUFANFF95 Real ID API is Live!"

@app.route('/gen')
def gen():
    try:
        u_name = request.args.get('name')
        u_pass = request.args.get('password')
        region = request.args.get('region', 'IND').upper()

        password = u_pass if u_pass else "TUFAN_" + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        final_name = u_name if u_name else "TUFAN" + str(random.randint(100, 999))
        
        # 1. Register
        reg_res = requests.post("https://100067.connect.garena.com/api/v2/oauth/guest:register", 
                                json={"app_id": 100067, "client_type": 2, "password": password, "source": 2}, timeout=15).json()
        uid = reg_res["data"]["uid"]

        # 2. Token
        tok_res = requests.post("https://100067.connect.garena.com/oauth/guest/token/grant", 
                                 data={"uid": uid, "password": password, "response_type": "token", "client_type": "2", "client_secret": HEX_KEY, "client_id": "100067"}, timeout=15).json()
        access_token = tok_res["access_token"]
        open_id = tok_res["open_id"]

        # 3. Major Register (Set Nickname)
        major_reg_url = "https://loginbp.ggblueshark.com/MajorRegister"
        if region in ["ME", "TH"]: major_reg_url = "https://loginbp.common.ggbluefox.com/MajorRegister"
        
        lang = REGION_LANG.get(region, "en")
        reg_payload = {1: final_name, 2: access_token, 3: open_id, 5: 102000007, 6: 4, 7: 1, 15: lang}
        requests.post(major_reg_url, data=aes_encrypt(build_proto(reg_payload).hex()), timeout=15)

        # 4. Major Login (To get Real Account ID)
        major_login_url = "https://loginbp.ggblueshark.com/MajorLogin"
        if region in ["ME", "TH"]: major_login_url = "https://loginbp.common.ggbluefox.com/MajorLogin"
        
        # simplified login payload logic
        login_payload = build_proto({1: open_id, 2: access_token, 3: lang})
        login_res = requests.post(major_login_url, data=aes_encrypt(login_payload.hex()), timeout=15)
        
        account_id = "N/A"
        if "eyJ" in login_res.text:
            jwt_start = login_res.text.find("eyJ")
            jwt_token = login_res.text[jwt_start:].split()[0].split('\\')[0].split('"')[0]
            account_id = get_account_id_from_jwt(jwt_token)

        return jsonify({
            "status": "success", 
            "uid": str(uid),
            "account_id": account_id, 
            "password": password, 
            "name": final_name, 
            "region": region
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def handler(event, context):
    return app(event, context)