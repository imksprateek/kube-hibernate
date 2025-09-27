from flask import Flask, request
import subprocess
import datetime
import threading
import time

app = Flask(__name__)

SLEEPINFO_NAME = "weekday-short-sleep"
NAMESPACE = "default"

# Track last request time
last_request_time = None
IDLE_TIMEOUT_MINUTES = 2  # If no traffic for 2 minutes, pods go back to sleep

def patch_sleepinfo(wake=True, minutes=2):
    now = datetime.datetime.now()
    target_time = (now + datetime.timedelta(minutes=minutes)).strftime("%H:%M")
    field = "wakeUpAt" if wake else "sleepAt"
    patch_cmd = [
        "kubectl", "patch", "sleepinfo", SLEEPINFO_NAME,
        "-n", NAMESPACE,
        "--type=merge",
        "-p", f'{{"spec":{{"{field}":"{target_time}"}}}}'
    ]
    result = subprocess.run(patch_cmd, capture_output=True, text=True)
    print(f"[{datetime.datetime.now()}] Patched {field} to {target_time}")
    print(result.stdout.strip(), result.stderr.strip())

def monitor_idle():
    global last_request_time
    while True:
        time.sleep(30)
        if last_request_time:
            elapsed = (datetime.datetime.now() - last_request_time).total_seconds() / 60
            if elapsed >= IDLE_TIMEOUT_MINUTES:
                print(f"[{datetime.datetime.now()}] No traffic for {IDLE_TIMEOUT_MINUTES} minutes. Putting pods to sleep.")
                patch_sleepinfo(wake=False)
                last_request_time = None  # Reset after sleeping

@app.route("/wake", methods=["GET", "POST"])
def wake_endpoint():
    global last_request_time
    last_request_time = datetime.datetime.now()
    patch_sleepinfo(wake=True)
    return "Pods wake-up triggered!", 200

if __name__ == "__main__":
    # Start idle monitor in background
    threading.Thread(target=monitor_idle, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
