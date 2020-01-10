import datetime
import bisect
import pytz
import dateutil.parser

CREW_TIME = datetime.timedelta(hours=1)
LOADING_TIME = datetime.timedelta(hours=3)
TRAVEL_TIME = datetime.timedelta(hours=1)
LOAD_AT_WH = datetime.timedelta(minutes=45)

class Job:
    # def parameters such as it can distinguish between jobs that require pickup, different items
    def __init__(self, jobId, vesselIMOID, vesselName, vesselCallsign, vesselLoadingLocation, vesselLoadingDateTime,
                 etb, etu, jobItems, jobOfflandItems, pickupDetails, qcStart, qcEnd, user, terminal, *args):
        self.job_id = jobId
        self.vessel_name = vesselName
        self.vessel_imo_id = vesselIMOID
        self.vessel_callsign = vesselCallsign
        self.vessel_loading_location = vesselLoadingLocation
        self.vessel_loading_datetime = vesselLoadingDateTime
        self.etb = etb
        self.etu = etu

        self.job_items = jobItems
        numOfPallets = 0
        numOfBundles = 0
        numOfOthers = 0
        for item in self.job_items: #equate all items to pallets or bundles
            if item["uom"] == "Pallet" or "Carton":
                numOfPallets += item["quantity"]
            elif item["uom"] == "Blue Bins":
                numOfPallets += 2 * item["quantity"]
            elif item["uom"] == "Bundle":
                numOfBundles += item["quantity"]
            else:  # other
                numOfOthers += item["quantity"]
        self.pallets = numOfPallets
        self.bundles = numOfBundles
        self.others = numOfOthers

        self.job_offland_items = jobOfflandItems
        self.pickup_details = pickupDetails
        if self.pickup_details:
            self.pickup_location = self.pickup_details[0]['pickupLocation']['addressString']
            self.pickup_time = dateutil.parser.parse(self.pickup_details[0]["pickupDateTime"]).astimezone(pytz.timezone("Asia/Singapore"))
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
        self.terminal = terminal

    def find_delivery_time(self):
        if self.vessel_loading_location == "PSA":
            if self.qc_start is not None and self.qc_end is not None:
                if self.qc_start > self.etu or self.qc_end < self.etb:  # No QC
                    self.delivery_time = self.etb + CREW_TIME #deliver after vessel berth and prep for loading
                else:
                    if self.is_delivery_before: # can deliver before QC
                        self.delivery_time = self.etb + CREW_TIME
                    else: #deliver 1 hour after QC ends
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
            if self.delivery_time - self.pickup_time <= datetime.timedelta(
                    hours=2):  # if time done pickup is less than 1.5 hours from delivery time
                return self.pickup_time.strftime("%m/%d/%Y, %H:%M:%S") + " at " + self.pickup_location
            else:
                new_time = self.delivery_time - datetime.timedelta(hours = 2)
                return "Current pick-up time (" + self.pickup_time.strftime("%m/%d/%Y, %H:%M:%S") + ") is too early. Suggested new pick-up time: " + new_time.strftime("%m/%d/%Y, %H:%M:%S")
        else:  # multiple pick-ups
            pick_ups = []
            for location in self.pickup_details:
                t = datetime.datetime.strptime(location['pickupDateTime'], "%Y-%m-%dT%H:%M:%S.%fz")
                pick_ups.append(t.strftime("%m/%d/%Y, %H:%M:%S") + " at " + location["pickupLocation"]["addressString"])
            return pick_ups

    def process_items(self):
        numOfPallets = self.pallets
        numOfBundles = self.bundles
        numOfOthers = self.others
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
        if self.terminal and other_job.terminal and self.terminal == other_job.terminal: #same destination
            p1 = self.pickup_time
            d1 = self.find_delivery_time()
            p2 = other_job.pickup_time
            d2 = other_job.find_delivery_time()
            delivery_diff = abs(d1-d2)
            if datetime.timedelta(hours=5) > delivery_diff >= datetime.timedelta(hours=3):# can deliver together as the delivery time is less than 5 hours apart and more than 3 hours apart
                print("delivery timings are suitable")
                if self.pickup_location is not None and other_job is not None and self.pickup_location == other_job.pickup_location: #same pickup location
                    print("Same pickup location")
                    if abs(p1-p2) > datetime.timedelta(minutes=45): #pick up at the same location should be less than 45 minutes to prevent waiting
                        print("Pickup times are too far. Change pickup time to pickup and deliver together")
                    else: #pick up at the same location are less than 45 minutes
                        print("Pick up and deliver together")
                    return True
                else: # different pickup location
                    if datetime.timedelta(hours=2.5) > abs(p1-p2) > LOAD_AT_WH + TRAVEL_TIME: #can pick up both
                        if p1 < p2: #pick up job 1 before pick up job 2
                            print("Pickup: " + str(self.job_id) + ", " + str(other_job.job_id))
                            if d1 < d2: #delivery to job 1 before delivery job 2
                                if p2 + LOAD_AT_WH + TRAVEL_TIME < d1: # check whether theres enough time to pick up both before delivering job 1
                                    print("Delivery: " + str(self.job_id) + ", " + str(other_job.job_id))
                                    return True
                                else:
                                    return False
                            else: #d2 first
                                if p2 + LOAD_AT_WH + TRAVEL_TIME < d2:# check whether theres enough time to pick up both before delivering to job 2
                                    print("Delivery: " + str(other_job.job_id) + ", " + str(self.job_id))
                        else: #p2 first
                            print("Pickup: " + str(other_job.job_id) + ", " + str(self.job_id))
                            if d1 < d2: #d1 first
                                if p1 + LOAD_AT_WH + TRAVEL_TIME < d1: # check whether theres enough time to pick up both before delivering to job 1
                                    print("Delivery: " + str(self.job_id) + ", " + str(other_job.job_id))
                                    return True
                                else:
                                    return False
                            else: #d2 first
                                if p1 + LOAD_AT_WH + TRAVEL_TIME < d2: # check whether theres enough time to pick up both before delivering to job 2
                                    print("Delivery: " + str(other_job.job_id) + ", " + str(self.job_id))
                    elif datetime.timedelta(hours=2.5) <= abs(p1-p2): #cannot pick up both
                        print("Pickup times are too far apart")
                        return False
                    else:
                        print("Pickup times are too close")
                        return False
            else: #cannot deliver together
                print("same destination but different timing")
                return False
        else:
            print("different destination")
            return False

    def assign_truck(self, truck):
        self.truck = truck.truck_id