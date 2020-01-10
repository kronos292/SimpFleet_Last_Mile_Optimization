class Trip:
    def __init__(self, job1, job2):
        self.job1 = job1
        self.job2 = job2
        self.pallets = job1.pallets + job2.pallets
        self.bundles = job1.bundles + job2.bundles
        self.others = job1.others + job2.others
        self.items = [self.pallets, self.bundles, self.others]

    def get_truck(self):
        if self.others == 0:
            if self.bundles == 0: # only pallets
                if self.pallets <= 2:
                    print("use a 10ft truck for " + str(self.pallets) + " pallets")
                elif 3 <= self.pallets <= 4:
                    print("use a 14ft truck for " + str(self.pallets) + " pallets")
                elif 4 < self.pallets <= 12:
                    print("use a 24ft truck for " + str(self.pallets) + " pallets")
                elif 12 < self.pallets < 15:
                    print("use a 28ft truck for " + str(self.pallets) + " pallets")
                else:
                    print("more than 1 truck needed for " + str(self.pallets) + " pallets")
            elif self.pallets == 0: # only bundles
                if self.bundles < 5:
                    print("use a 24ft truck for " + str(self.bundles) + " bundles")
                else:
                    print("more than 1 truck needed for " + str(self.bundles) + " bundles")
            else: # both bundles and pallets
                if self.bundles <= 4 and self.pallets <= 6:
                    print("use a 24ft truck for " + str(self.bundles) + " bundles" + " and " + str(self.pallets) + "pallets")
                else:
                    print("more than 1 truck needed for " + str(self.bundles) + " bundles" + " and " + str(self.pallets) + "pallets")
        else:
            print("Other items. Please contact clients")