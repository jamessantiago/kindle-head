import codecs
from esxisnmp import EsxiSnmp
from nginxstats import NginxStats
from secrets import SNMP_HOST, SNMP_USER, SNMP_AUTHKEY, SNMP_PRIVKEY, SNMP_NIC, NGINX_HOST
import pickle
import time
from datetime import datetime, date
import subprocess
import os
import pathlib

NET_STATS = 'esxi_net_stats.pkl'
os.chdir(pathlib.Path(__file__).parent.absolute())

def human_bytes(num, is_kibi=True, suffix='B'):
    if is_kibi:
        units = ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']
        byte_scale = 1024.0
    else:
        units = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']
        byte_scale = 1000.0

    for unit in units:
        if abs(num) < byte_scale:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= byte_scale
    return "%.1f%s%s" % (num, 'Y', suffix)

def usbnet_ready():
    for netdev in os.listdir("/sys/class/net/"):
        if netdev == "usb0":
            return True

    return False


if __name__ == "__main__":
    if not usbnet_ready():
        raise RuntimeException("The usbnet device is not ready")

    esxi = EsxiSnmp(SNMP_HOST, SNMP_USER, SNMP_AUTHKEY, SNMP_PRIVKEY)
    try:
        cpu = str(esxi.get_cpu()) + "%"
    except Exception as e:
        print(e)
        cpu = "N/A"

    try:
        mem = str(esxi.get_mem()) + "%"
    except Exception as e:
        print(e)
        mem = "N/A"

    if os.path.isfile(NET_STATS):
        with open(NET_STATS, 'rb') as f:
            last_stats = pickle.load(f)
    else:
        last_stats = None

    try:
        cur_net_in = esxi.get_nic_in(SNMP_NIC)
        cur_net_out = esxi.get_nic_out(SNMP_NIC)
        now = time.mktime(datetime.today().timetuple())
        stats = {"now": now, "in": cur_net_in, "out": cur_net_out}
        with open(NET_STATS, 'wb') as f:
            pickle.dump(stats, f)
        if last_stats and last_stats["now"] != now:
            net_in = float(cur_net_in - last_stats["in"]) / float(now - last_stats["now"])
            net_out = float(cur_net_out - last_stats["out"]) / float(now - last_stats["now"])
            net_in_pretty = human_bytes(net_in)
            net_out_pretty = human_bytes(net_out)
        else:
            net_in_pretty = "N/A"
            net_out_pretty = "N/A"
    except Exception as e:
        print(e)
        net_in_pretty = "N/A"
        net_out_pretty = "N/A"

    nginx = NginxStats(NGINX_HOST)
    try:
        connections = nginx.get_active_connections()
    except Exception as e:
        print(e)
        connections = "N/A"

    template = codecs.open('template.svg', 'r', encoding='utf-8').read()

    template = template.replace("S1", cpu)
    template = template.replace("S2", mem)
    template = template.replace("S3", net_out_pretty)
    template = template.replace("S4", net_in_pretty)
    template = template.replace("S5", connections)
    template = template.replace("S6", time.strftime("%Y-%m-%d %H:%M"))

    codecs.open('working.svg', 'w', encoding='utf-8').write(template)
    subprocess.call("rsvg-convert --background-color=white -o working.png working.svg", shell=True)
    subprocess.call("pngcrush -force -c 0 working.png image.png", shell=True)
    subprocess.call('sshpass -p "" scp -l 15 image.png root@192.168.2.2:/mnt/us/timelit/server_image/image.png', shell=True)
    os.remove("working.png")
    os.remove("working.svg")


