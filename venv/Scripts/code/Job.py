import datetime

CREW_TIME = datetime.timedelta(hours = 1)
LOADING_TIME = datetime.timedelta(hours = 3)

class Job:
    #def parameters such as it can distinguish between jobs that require pickup, different items
    def __init__(self, jobId, vesselIMOID, vesselName, vesselCallsign, vesselLoadingLocation, vesselLoadingDateTime, etb, etu,jobItems, jobOfflandItems, pickupDetails, qcStart, qcEnd, user, *args):
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
            self.pickup_time = datetime.datetime.strptime(self.pickup_details[0]['pickupDateTime'],"%Y-%m-%dT%H:%M:%S.%fz")
        self.qc_start = qcStart
        self.qc_end = qcEnd
        self.user_company = user
        if self.qc_start != None and self.qc_end != None:
            self.time_before = self.qc_start - self.etb - CREW_TIME
            self.time_after = self.etu - self.qc_end
            self.is_delivery_before = self.time_before > LOADING_TIME
        else:
            self.time_before = None
            self.time_after = None
            self.is_delivery_before = None

    def find_delivery_time(self):
        if self.vessel_loading_location == "PSA":
            if self.qc_start != None and self.qc_end != None:
                if self.qc_start > self.etu or self.qc_end < self.etb: # No QC
                    self.delivery_time = self.etb + CREW_TIME
                else:
                    if self.is_delivery_before == True:
                        self.delivery_time = self.etb + CREW_TIME
                    else:
                        self.delivery_time = self.qc_end + datetime.timedelta(hours = 1)
            else: # No QC
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
            time = self.pickup_time + datetime.timedelta(hours = 1.5)
            self.delivery_time = self.find_delivery_time()
            if self.delivery_time - time < datetime.timedelta(hours = 4): # if time done pickup is less than 4 hours from delivery time
                return self.pickup_time.strftime("%m/%d/%Y, %H:%M:%S") + " at " + self.pickup_location
            else:
                return "Pick-up time is too early. Suggest new pick-up time or go back to warehouse after pick-up"
        else: # multiple pick-ups
            pick_ups = []
            for location in self.pickup_details:
                t = datetime.datetime.strptime(location['pickupDateTime'],"%Y-%m-%dT%H:%M:%S.%fz")
                pick_ups.append(t.strftime("%m/%d/%Y, %H:%M:%S") + " at " + location["pickupLocation"]["addressString"])
            return pick_ups


