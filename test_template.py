import requests, os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("HA_API_KEY")
url = "http://10.0.0.100:8123/api/template"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
template = """
{% set ns = namespace(mapping=[]) %}
{% for state in states %}
  {% set dev_id = device_id(state.entity_id) %}
  {% if dev_id %}
    {% set entries = device_attr(dev_id, 'config_entries') %}
  {% endif %}
{% endfor %}
{{ ns.mapping | to_json }}
"""
res = requests.post(url, headers=headers, json={"template": template})
print(res.status_code)
print(res.text)
