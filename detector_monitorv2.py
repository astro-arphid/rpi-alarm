import time
import requests

API_URL = "https://online.igwn.org/grafana/api"

TIMESTAMP_15_MINUTES = 900_000
TIMESTAMP_TO = int(time.time() * 1000) # now
TIMESTAMP_FROM = TIMESTAMP_TO - TIMESTAMP_15_MINUTES

mapping = {
    "GEO": "GEO600",
    "H1" : "LIGO Hanford",
    "K1" : "KAGRA",
    "L1" : "LIGO Livingston",
    "V1" : "Virgo",
}

def get_status_frames(data):
    return data["results"]["A"]["frames"]

def get_status_from_frame(frame):
    return frame["data"]["values"][1][0]

def get_name_from_frame(frame):
    return mapping[frame["schema"]["fields"][1]["labels"]["ifo"]]

def get_data():
    """Returns empty list on failure"""
    try:
        json_data = {
            'intervalMs': 60000,
            'maxDataPoints': 617,
            'timeRange': {
                'from': str(TIMESTAMP_FROM),
                'to': str(TIMESTAMP_TO),
            },
        }

        request = requests.request("POST", f"{API_URL}/public/dashboards/1a0efabe65384a7287abfcc1996e4c4d/panels/4/query", json=json_data)
        request.raise_for_status()
        return request.json()
    
    except requests.HTTPError:
        print("failed to fetch data..")
        return []

result = get_data()
status_frames = get_status_frames(result)

for frame in status_frames:
    status = get_status_from_frame(frame)
    name = get_name_from_frame(frame)

    print(name, status)
#return export,statuses, names
