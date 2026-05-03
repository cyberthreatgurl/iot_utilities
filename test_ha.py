import requests, os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("HA_API_KEY")
url = "http://10.0.0.100:8123/api/states"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
res = requests.get(url, headers=headers)
for s in res.json():
    print(s["attributes"])
    break
