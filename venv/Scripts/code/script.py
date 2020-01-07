import json
import datetime
import pprint
from Job import Job
from Truck import Truck

TRAVEL_TIME = datetime.timedelta(hours = 2)

with open('truck_test.json', 'r') as f:
    jobs_dict = json.load(f)

with open('truck.json', 'r') as f:
    truck_dict = json.load(f)

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
    vessel_loading_datetime = datetime.datetime.strptime(job["vesselLoadingDateTime"], "%Y-%m-%dT%H:%M:%S.%fz")
    if vessel_loading_location == "PSA":
        etb = datetime.datetime.strptime(job["psaBerthingDateTime"], "%Y-%m-%dT%H:%M:%S.%fz")
        etu = datetime.datetime.strptime(job["psaUnberthingDateTime"], "%Y-%m-%dT%H:%M:%S.%fz")
    else:
        etb = None
        etu = None
    job_items = job["jobItems"]
    job_offland_items = job["jobOfflandItems"]
    pickup_details = job["pickupDetails"]
    if job["psaQCStart"] is not None and job["psaQCEnd"] is not None:
        qc_start = datetime.datetime.strptime(job["psaQCStart"], "%Y-%m-%dT%H:%M:%S.%fz")
        qc_end = datetime.datetime.strptime(job["psaQCEnd"], "%Y-%m-%dT%H:%M:%S.%fz")
    else:
        qc_start = None
        qc_end = None
    user_company = job["userCompany"]

    j = Job(job_id, vessel_imo_id, vessel_name, vessel_callsign, vessel_loading_location, vessel_loading_datetime, etb,
            etu, job_items, job_offland_items, pickup_details, qc_start, qc_end, user_company)
    unassigned_jobs_list.append(j)
    result_dict['schedule'].append({
        "job": j.job_id,
        "delivery time": j.find_delivery_time().strftime("%m/%d/%Y, %H:%M:%S"),
        "user company": j.user_company,
        "location": j.vessel_loading_location,
        "pick up": j.check_pickup_time(),
        "items": j.process_items()
    })

for truck in truck_dict:
    truck_id = truck["truckId"]
    company = truck["company"]
    size = truck["size"]

    t = Truck(truck_id, company, size)
    trucks_list.append(t)

for job in unassigned_jobs_list:
    assigned = False
    for truck in trucks_list:
        if not job.pickup_details:
            if truck.finish + TRAVEL_TIME < job.find_delivery_time():
                job.assign_truck(truck)
                truck.take_job(job)
                assigned = True
        else:
            if truck.finish + TRAVEL_TIME < job.pickup_time:
                job.assign_truck(truck)
                truck.take_job(job)
                assigned = True
        if assigned:
            unassigned_jobs_list.remove(job)
            break
    result_dict['schedule'].append({
        "job": job.job_id,
        "delivery time": job.find_delivery_time().strftime("%m/%d/%Y, %H:%M:%S"),
        "user company": job.user_company,
        "location": job.vessel_loading_location,
        "pick up": job.check_pickup_time(),
        "items": job.process_items(),
        "truck": job.truck
    })




pp = pprint.PrettyPrinter(indent=4)
# pp.pprint(sorted(result_dict.items(), key=lambda x: x[1]))
pp.pprint(sorted(result_dict['schedule'], key = lambda x:x['delivery time']))

