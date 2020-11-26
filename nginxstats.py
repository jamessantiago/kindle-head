import requests
import re

class NginxStats:
    def __init__(self, host):
        self.url = f'http://{host}/nginx_status'

    def get_active_connections(self):
        r = requests.get(self.url)
        match = re.search(r"Active connections: (\d+)", r.text)
        if match:
            return match[1]
        else:
            return None
