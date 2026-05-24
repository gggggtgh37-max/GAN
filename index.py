from flask import Flask, request, jsonify
import requests
import random
import string
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

# --- API ROUTES ---
@app.route('/')
def home():
    return "TUFANFF95 Custom API is Live!"

@app.route('/gen')
def gen():
    try:
        # યુઝર પાસેથી ડેટા લેવો
        u_name = request.args.get('name')
        u_pass = request.args.get('password')
        region = request.args.get('region', 'IND').upper()

        # જો પાસવર્ડ ના આપ્યો હોય તો રેન્ડમ બનાવો
        if u_pass:
            password = u_pass
        else:
            password = "TUFANFF95_" + ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # જો નામ ના આપ્યો હોય તો રેન્ડમ બનાવો
        if u_name:
            final_name = u_name
        else:
            final_name = "TUFAN" + str(random.randint(100, 999))
        
        # 1. Register Garena Guest
        reg_res = requests.post("https://100067.connect.garena.com/api/v2/oauth/guest:register", 
                                json={"app_id": 100067, "client_type": 2, "password": password, "source": 2}, timeout=15).json()
        
        if "data" not in reg_res:
            return jsonify({"status": "error", "message": "Registration Failed", "details": reg_res})
            
        uid = reg_res["data"]["uid"]

        # 2. Token Grant
        tok_res = requests.post("https://100067.connect.garena.com/oauth/guest/token/grant", 
                                 data={"uid": uid, "password": password, "response_type": "token", "client_type": "2", "client_secret": HEX_KEY, "client_id": "100067"}, timeout=15).json()
        
        access_token = tok_res["access_token"]
        open_id = tok_res["open_id"]

        # 3. Major Register (Set Name)
        major_url = "https://loginbp.ggblueshark.com/MajorRegister"
        if region in ["ME", "TH"]: major_url = "https://loginbp.common.ggbluefox.com/MajorRegister"
        
        lang = REGION_LANG.get(region, "en")
        payload = {1: final_name, 2: access_token, 3: open_id, 5: 102000007, 6: 4, 7: 1, 13: 1, 15: lang}
        requests.post(major_url, data=aes_encrypt(build_proto(payload).hex()), timeout=15)

        return jsonify({
            "status": "success", 
            "uid": str(uid), 
            "password": password, 
            "name": final_name, 
            "region": region
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Vercel needs this
def handler(event, context):
    return app(event, context)