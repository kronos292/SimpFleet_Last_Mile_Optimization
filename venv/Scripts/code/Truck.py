import datetime
class Truck:
    def __init__(self, truck_id, company, size):
        self.truck_id = truck_id
        self.company = company
        self.size = size
        self.jobs = []
        self.finish = datetime.datetime.today()

    def take_job(self, job):
        self.jobs.append(job)
        self.finish = job.find_delivery_time()