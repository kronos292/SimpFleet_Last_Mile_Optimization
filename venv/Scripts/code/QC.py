class PC:
    qc_start
    qc_end
    jobID
    berth

    def __int__(self, qc_start, qc_end):
        self.qc_start = qc_start
        self.qc_end = qc_end

    def tag_jobid(self, jobID):
        self.jobID = jobID

    def update_qcStart(self, new_start):
        self.qc_start = new_start
    def update_qcEnd(self, new_end):
        self.qc_end = new_end
