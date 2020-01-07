import datetime
import bisect

CREW_TIME = datetime.timedelta(hours=1)
LOADING_TIME = datetime.timedelta(hours=3)
TRAVEL_TIME = datetime.timedelta(hours=2)
LOAD_AT_WH = datetime.timedelta(hours=1.5)


class Job:
    # def parameters such as it can distinguish between jobs that require pickup, different items
    def __init__(self, jobId, vesselIMOID, vesselName, vesselCallsign, vesselLoadingLocation, vesselLoadingDateTime,
                 etb, etu, jobItems, jobOfflandItems, pickupDetails, qcStart, qcEnd, user, *args):
        self.job_id = jobId
        self.vessel_name = vesselName
        self.vessel_imo_id = vesselIMOID
        self.vessel_callsign = vesselCallsign
        self.vessel_loading_location = vesselLoadingLocation
        self.vessel_loading_datetime = vesselLoadingDateTime
        self.etb = etb
        self.etu = etu
        self.job_items = jobItems
        self.job_offland_items = jobOfflandItems
        self.pickup_details = pickupDetails
        if self.pickup_details:
            self.pickup_location = self.pickup_details[0]['pickupLocation']['addressString']
            self.pickup_time = datetime.datetime.strptime(self.pickup_details[0]['pickupDateTime'],
                                                          "%Y-%m-%dT%H:%M:%S.%fz")
        else:
            self.pickup_location = None
            self.pickup_time = None
        self.qc_start = qcStart
        self.qc_end = qcEnd
        self.user_company = user
        if self.qc_start is not None and self.qc_end is not None:
            self.time_before = self.qc_start - self.etb - CREW_TIME
            self.time_after = self.etu - self.qc_end
            self.is_delivery_before = self.time_before > LOADING_TIME
        else:
            self.time_before = None
            self.time_after = None
            self.is_delivery_before = None
        self.truck = None

    def find_delivery_time(self):
        if self.vessel_loading_location == "PSA":
            if self.qc_start is not None and self.qc_end is not None:
                if self.qc_start > self.etu or self.qc_end < self.etb:  # No QC
                    self.delivery_time = self.etb + CREW_TIME
                else:
                    if self.is_delivery_before:
                        self.delivery_time = self.etb + CREW_TIME
                    else:
                        self.delivery_time = self.qc_end + datetime.timedelta(hours=1)
            else:  # No QC
                self.delivery_time = self.etb + CREW_TIME
        else:
            self.delivery_time = self.vessel_loading_datetime
        return self.delivery_time

    def update_qcStart(self, new_start):
        self.qc_start = new_start
        self.delivery_time = self.find_delivery_time()

    def update_qcEnd(self, new_end):
        self.qc_end = new_end
        self.delivery_time = self.find_delivery_time()

    def update_etb(self, new_etb):
        self.etb = new_etb
        self.delivery_time = self.find_delivery_time()

    def update_etu(self, new_etu):
        self.etu = new_etu
        self.delivery_time = self.find_delivery_time()

    def check_pickup_time(self):
        if not self.pickup_details:
            return "No pick-up required"
        elif len(self.pickup_details) == 1:
            time = self.pickup_time + LOAD_AT_WH
            self.delivery_time = self.find_delivery_time()
            if self.delivery_time - time < datetime.timedelta(
                    hours=4):  # if time done pickup is less than 4 hours from delivery time
                return self.pickup_time.strftime("%m/%d/%Y, %H:%M:%S") + " at " + self.pickup_location
            else:
                return "Pick-up time is too early. Suggest new pick-up time or go back to warehouse after pick-up"
        else:  # multiple pick-ups
            pick_ups = []
            for location in self.pickup_details:
                t = datetime.datetime.strptime(location['pickupDateTime'], "%Y-%m-%dT%H:%M:%S.%fz")
                pick_ups.append(t.strftime("%m/%d/%Y, %H:%M:%S") + " at " + location["pickupLocation"]["addressString"])
            return pick_ups

    def process_items(self):
        numOfPallets = 0
        numOfBundles = 0
        numOfOthers = 0
        for item in self.job_items:
            if item["uom"] == "Pallet" or "Carton":
                numOfPallets += item["quantity"]
            elif item["uom"] == "Blue Bins":
                numOfPallets += 2 * item["quantity"]
            elif item["uom"] == "Bundle":
                numOfBundles += item["quantity"]
                return "Bundle requires a 24ft truck"
            else:  # other
                numOfOthers += item["quantity"]
                return "Non-standardised items. Contact suppliers for more details"
        items = []
        items.append({
            "Pallet: " + str(numOfPallets),
            "Bundle: " + str(numOfBundles),
            "Other: " + str(numOfOthers)
        })
        return items

    def num_of_trucks(self):
        items = self.process_items()
        if int(items["Bundle"]) > 0:
            return 1
        else:
            if int(items["Pallet"]) < 14:
                return 1
            else:
                return int(items["Pallet"]) // 14 + 1

    def use_same_truck(self, other_job):
        p1 = self.pickup_time, d1 = self.find_delivery_time()
        p2 = other_job.pickup_time, d2 = other_job.find_delivery_time()
        if p1 + LOAD_AT_WH + TRAVEL_TIME < p2:
            if p2 + LOAD_AT_WH + TRAVEL_TIME < d1:
                if d1 + LOADING_TIME + TRAVEL_TIME < d2:
                    return "pick up " + self.job_id + " --> pick up " + other_job.job_id + " --> deliver " + self.job_id + " --> deliver " + other_job.job_id
            elif p2 + LOAD_AT_WH + TRAVEL_TIME < d2:
                if d2 + LOADING_TIME + TRAVEL_TIME < d1:
                    return "pick up " + self.job_id + " --> pick up " + other_job.job_id + " --> deliver " + other_job.job_id + " --> deliver " + self.job_id
        elif p2 + LOAD_AT_WH + TRAVEL_TIME < p1:
            if p1 + LOAD_AT_WH + TRAVEL_TIME < d1:
                if d1 + LOADING_TIME + TRAVEL_TIME < d2:
                    return "pick up " + other_job.job_id + " --> pick up " + self.job_id + " --> deliver " + self.job_id + " --> deliver " + other_job.job_id
            elif p1 + LOAD_AT_WH + TRAVEL_TIME < d2:
                if d2 + LOADING_TIME + TRAVEL_TIME < d1:
                    return "pick up " + other_job.job_id + " --> pick up " + self.job_id + " --> deliver " + other_job.job_id + " --> deliver " + self.job_id
        else:
            return "Impossible"

    def assign_truck(self, truck):
        self.truck = truck.truck_id
