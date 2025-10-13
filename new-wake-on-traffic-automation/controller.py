import os
import time
import pytz
import requests
from datetime import datetime
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
from kubernetes.dynamic import DynamicClient

# === CONFIGURATION ===
TARGET_NAMESPACE = "default"
FRONTEND_SERVICE = "frontend-external"
CHECK_INTERVAL = 60  # seconds
# PROMETHEUS_URL = "http://prometheus-server.default.svc.cluster.local:80"  # Change if different
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus-server.default.svc.cluster.local:80")

WAKE_THRESHOLD = 1   # requests per minute

# === SETUP ===
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

k8s = client.AppsV1Api()
dyn_client = DynamicClient(client.ApiClient())
prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)

# === HELPERS ===
def list_deployments():
    return k8s.list_namespaced_deployment(namespace=TARGET_NAMESPACE).items

def scale_deployment(name, replicas):
    dep = k8s.read_namespaced_deployment(name, TARGET_NAMESPACE)
    if dep.spec.replicas != replicas:
        dep.spec.replicas = replicas
        k8s.patch_namespaced_deployment(name, TARGET_NAMESPACE, dep)
        print(f"[Controller] Set {name} replicas to {replicas}")

def get_traffic_rate():
    """
    Query Prometheus to get current request rate hitting the frontend-external service.
    Adjust the metric name depending on your Prometheus setup.
    """
    query = f'rate(nginx_ingress_controller_requests{{{{job="nginx-ingress"}}}}[2m])'
 
    try:
        result = prom.custom_query(query=query)
        if result:
            value = float(result[0]['value'][1])
            print(f"[Metrics] Current traffic rate: {value} req/s")
            return value
    except Exception as e:
        print(f"[Warning] Prometheus query failed: {e}")
    return 0.0

def is_sleep_time():
    """
    Read kube-green SleepInfo CR to determine current sleep schedule.
    """
    sleepinfo_api = dyn_client.resources.get(api_version="kube-green.com/v1alpha1", kind="SleepInfo")
    infos = sleepinfo_api.get(namespace=TARGET_NAMESPACE)
    tz = pytz.timezone("Asia/Kolkata")

    now = datetime.now(tz)
    weekday = now.isoweekday()  # 1=Mon .. 7=Sun

    for si in infos.items:
        weekdays = si.spec.get("weekdays", "")
        if str(weekday) in weekdays or weekdays == "1-5" and weekday <= 5:
            sleep_at = si.spec.get("sleepAt", "00:00")
            wake_at = si.spec.get("wakeUpAt", "09:00")

            sleep_hour, sleep_min = map(int, sleep_at.split(":"))
            wake_hour, wake_min = map(int, wake_at.split(":"))

            now_mins = now.hour * 60 + now.minute
            sleep_mins = sleep_hour * 60 + sleep_min
            wake_mins = wake_hour * 60 + wake_min

            if sleep_mins <= now_mins < wake_mins:
                return True
    return False

# === MAIN LOOP ===
def main():
    print("[Controller] Starting kube-green-traffic-waker")
    sleeping = False

    while True:
        traffic_rate = get_traffic_rate()
        in_sleep = is_sleep_time()

        if in_sleep:
            if traffic_rate > WAKE_THRESHOLD:
                print("[Controller] 🚨 Traffic detected during sleep, waking deployments!")
                for d in list_deployments():
                    if d.spec.replicas == 0:
                        scale_deployment(d.metadata.name, 1)
                sleeping = False
            else:
                print("[Controller] 🌙 Within sleep window, no active traffic.")
        else:
            print("[Controller] ☀️ Outside sleep window, ensure normal operation.")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
