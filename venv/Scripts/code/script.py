import json
import datetime
import pprint
from Job import Job
from Truck import Truck
from Trip import Trip
import pytz
import dateutil.parser

TRAVEL_TIME = datetime.timedelta(hours=1)

with open('group_trip_test.json', 'r') as f:
    jobs_dict = json.load(f)

result_dict = {}
result_dict['schedule'] = []
unassigned_jobs_list = []
trucks_list = []

for job in jobs_dict:
    job_id = job["jobId"]
    vessel_imo_id = job["vesselIMOID"]
    vessel_name = job["vesselName"]
    vessel_callsign = job["vesselCallsign"]
    vessel_loading_location = job["vesselLoadingLocation"]
    vessel_loading_datetime = dateutil.parser.parse(job["vesselLoadingDateTime"]).astimezone(pytz.timezone("Asia/Singapore")) #datetime.datetime.strptime(job["vesselLoadingDateTime"], "%Y-%m-%dT%H:%M:%S.%fz")
    if vessel_loading_location == "PSA":
        etb = dateutil.parser.parse(job["psaBerthingDateTime"]).astimezone(pytz.timezone("Asia/Singapore"))
        etu = dateutil.parser.parse(job["psaUnberthingDateTime"]).astimezone(pytz.timezone("Asia/Singapore"))
    else:
        etb = None
        etu = None
    job_items = job["jobItems"]
    job_offland_items = job["jobOfflandItems"]
    pickup_details = job["pickupDetails"]
    if job["psaQCStart"] is not None and job["psaQCEnd"] is not None:
        qc_start = dateutil.parser.parse(job["psaQCStart"]).astimezone(pytz.timezone("Asia/Singapore"))
        qc_end = dateutil.parser.parse(job["psaQCEnd"]).astimezone(pytz.timezone("Asia/Singapore"))
    else:
        qc_start = None
        qc_end = None
    user_company = job["userCompany"]
    terminal = job["terminal"]

    j = Job(job_id, vessel_imo_id, vessel_name, vessel_callsign, vessel_loading_location, vessel_loading_datetime, etb,
            etu, job_items, job_offland_items, pickup_details, qc_start, qc_end, user_company, terminal)
    unassigned_jobs_list.append(j)
    result_dict['schedule'].append({
        "job": j.job_id,
        "delivery time": j.find_delivery_time().strftime("%m/%d/%Y, %H:%M:%S"),
        "user company": j.user_company,
        "location": j.vessel_loading_location,
        "pick up": j.check_pickup_time(),
        "items": j.process_items(),
        "terminal": j.terminal
    })

pp = pprint.PrettyPrinter(indent=4)
unassigned_jobs_list.sort(key=lambda x: x.find_delivery_time())
for i in range(len(unassigned_jobs_list) - 1):
        j = unassigned_jobs_list[i]
        for k in range(1, len(unassigned_jobs_list) - i):
            o = unassigned_jobs_list[i+k]
            print(str(j.job_id) + " and " + str(o.job_id) + ": " + str(j.use_same_truck(o)))
            if (j.use_same_truck(o)):
                trip = Trip(j, o)
                print(trip.get_truck())

pp.pprint(sorted(result_dict['schedule'], key = lambda x:x['delivery time']))