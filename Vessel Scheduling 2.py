#!/usr/bin/env python
# coding: utf-8

# In[1]:


from datetime import datetime
from datetime import timedelta
from pandas import DataFrame, read_csv
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go


# In[2]:


JP_LOADING_TIME = timedelta(hours=1)
TRAVEL_TIME = timedelta(hours=1)
MAX_JP_WAIT_TIME = timedelta(hours=1)
PSA_LOADING_TIME= timedelta(hours=2)
WAREHOUSE_LOADING = timedelta(minutes=30)
DRIVER_HOURS= timedelta(hours=12)
MAX_CARGO = 12
CREW_TIME = timedelta(hours=1)


# In[3]:
file = '[BVPS]_Time_range_to_avoid_for_Ship_Supply_[20190731][1000].xls'

def getDriverDetails(file):

    df = pd.read_excel(file)

    for header in ['ETB', 'ETU', 'QC Seq Time From', 'QC Seq Time To']:
        for i in range(len(df[header])):
            day = int(df[header][i][:2])
            month = int(df[header][i][3:5])
            year = int(df[header][i][6:10])
            hour = int(df[header][i][11:13])
            minute = int(df[header][i][14:16])
            second = int(df[header][i][17:19])
            df[header][i]= datetime(year, month, day, hour, minute, second, 0)

    df = df.drop(columns=['Terminal', 'Voyage', 'Berthing Sequence'])
    df['timeBefore'] = df['QC Seq Time From'] - df['ETB']
    df['timeAfter'] = df['ETU'] - df['QC Seq Time To'] 
    df['Quantity'] = 2
    df['Type']='Berthing'

    ## Sort to Priority
    loadBefore = df[df['timeBefore'].apply(lambda o:o.seconds/60 > 90)]
    loadBefore.sort_values(by=['QC Seq Time From','timeBefore'], inplace=True)
    loadBefore = loadBefore.reset_index()
    loadBefore = loadBefore.drop(columns=['index'])
    loadAfter = df[df['timeBefore'].apply(lambda o:o.seconds/60 <= 90)]
    loadAfter.sort_values(by=['timeAfter'], inplace=True, ascending= True)
    loadAfter.sort_values(by=['QC Seq Time To'], inplace=True)
    loadAfter = loadAfter.reset_index()
    loadAfter = loadAfter.drop(columns=['index'])
    df = pd.concat([loadBefore, loadAfter])
    df = df.reset_index()
    df = df.drop(columns=['index'])

    def addAnchorageEvent(name, loadingTime, quantity):
        return {
            "Vessel Name": name,
            "ETB": loadingTime,
            "QC Seq Time From": loadingTime,
            "ETU": loadingTime + JP_LOADING_TIME,
            "QC Seq Time To": loadingTime + JP_LOADING_TIME,
            "timeBefore": timedelta(minutes=5),
            "timeAfter": timedelta(minutes=5),
            'Total Free Time': timedelta(minutes=10),
            "Quantity": quantity,
            "Type": 'Anchorage',
        }

    dict_anchorage=[]
    dict_anchorage.append(addAnchorageEvent('Test 1', datetime(2019, 7, 31, hour=10, minute=0, second=0), 1))
    dict_anchorage.append(addAnchorageEvent('Test 2', datetime(2019, 7, 31, hour=14, minute=0, second=0), 1))
    dict_anchorage.append(addAnchorageEvent('Test 3', datetime(2019, 7, 31, hour=18, minute=0, second=0), 1))
    df_anchorage = pd.DataFrame(dict_anchorage)

    df['Total Free Time'] = df['timeBefore'] + df['timeAfter']
    df.sort_values(by=['Total Free Time','ETB'], inplace=True)
    df.sort_values(by=['QC Seq Time From'], inplace=True)
    df = df.reset_index()
    df = df.drop(columns=['index'])

    df = pd.concat([df_anchorage,df])

    df['Priority'] = 0
    df = df.reset_index()
    df = df.drop(columns=['index'])

    def assignPriority():
        priority = 1
        assigned = 0
        while assigned != len(df):
            for index, row in df.iterrows():
                df['Priority'][index]=priority
                priority+=1
                assigned+=1
    assignPriority()

    def assignDeliveryTime():
        df['deliveryTime'] = None
        df['Assign'] = 'Wait'
        assigned = 0
        drivers = []
        driverIndex = 0
        
        ## Add anchorage Delivery Time
        for index, row in df.iterrows():
            if df['Type'][index]=='Anchorage':
                df['deliveryTime'][index] = df['ETB'][index] 
        
        ## Assign Driver & DeliveryTime for Anchorage
        while assigned < len(df[df['Type']=='Anchorage']):
            #Create new Driver
            driverIndex += 1
            Driver = {'Name':'Driver ' + str(driverIndex),
                    'First Deliver':None,
                    'Leave Warehouse':None,
                    'End Work':None,
                    'Leave Port':None,
                    'Cargo':0,
                    'Jobs':[],
                   }
            for index, row in df.iterrows():
                if df['Type'][index]=='Anchorage':
                    ## Check if first delivery
                    if (Driver['Cargo'] == 0):
                        if (df['Assign'][index] == 'Wait') :
                            firstDelivery = df['deliveryTime'][index]
                            Driver['First Deliver'] = firstDelivery
                            Driver['Leave Warehouse'] = firstDelivery - TRAVEL_TIME
                            Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                            Driver['Leave Port'] = Driver["First Deliver"] + JP_LOADING_TIME
                            df['Assign'][index] = Driver['Name']
                            Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                            Driver['Cargo'] += df['Quantity'][index] 
                            assigned +=1
                    else:
                        if (df['Assign'][index] == 'Wait'):
                            if (Driver['Cargo'] + df['Quantity'][index]) <= MAX_CARGO:
                                if (df['deliveryTime'][index] <= (Driver['Leave Port'] + MAX_JP_WAIT_TIME)) & (df['deliveryTime'][index] >= Driver['Leave Port']):
                                    if (df['deliveryTime'][index] + JP_LOADING_TIME + TRAVEL_TIME) < Driver['End Work']:
                                        df['Assign'][index] = Driver['Name']
                                        Driver['Leave Port'] = df['deliveryTime'][index] + JP_LOADING_TIME
                                        Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                        Driver['Cargo'] += df['Quantity'][index] 
                                        assigned +=1
            drivers.append(Driver)
            
        ## Account for traveling time & Loading & traveling to PSA
        for Driver in drivers:
            Driver['Leave Port'] = Driver['Leave Port'] + TRAVEL_TIME + WAREHOUSE_LOADING + TRAVEL_TIME
            Driver['Cargo'] = 0
            
    
        ## Added all crew time delay due to busy crew members
        for index, row in df.iterrows():
            df['ETB'][index] += CREW_TIME
            ## if Not enough time to load auto set delivery time to QC END
            if ((df['QC Seq Time From'][index] - df['ETB'][index]) < PSA_LOADING_TIME) & ((df['ETU'][index] - df['QC Seq Time To'][index]) < PSA_LOADING_TIME):
                df['deliveryTime'][index] = df['QC Seq Time To'][index] 
                
        ##Assign rest of driver    
        while assigned < len(df):
            for Driver in drivers:
                for index, row in df.iterrows():
                    if df['Type'][index]=='Berthing':
                        if (df['Assign'][index] == 'Wait'):
                            if (Driver['Cargo'] + df['Quantity'][index]) <= MAX_CARGO:
                                ## Check if Driver still has work time
                                if (Driver['Leave Port']+PSA_LOADING_TIME) <= (Driver['End Work'] - TRAVEL_TIME):
                                    ## If Already have fixed delivery time then use that time
                                    if df['deliveryTime'][index] != None:
                                        ##If delivery time after job
                                        if (df['deliveryTime'][index] >= Driver['Leave Port']) & (df['deliveryTime'][index] <= Driver['End Work'] - TRAVEL_TIME):
                                            
                                            df['Assign'][index] = Driver['Name']
                                            Driver['Leave Port'] = df['deliveryTime'][index] + PSA_LOADING_TIME
                                            Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                            Driver['Cargo'] += df['Quantity'][index] 
                                            assigned +=1
                                        elif df['deliveryTime'][index] >= (Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS):
                                            if len(list(filter(lambda o: o['Type'] == 'Anchorage', Driver['Jobs']))) == 0:
                                                if (df['deliveryTime'][index] + PSA_LOADING_TIME) <= Driver['First Deliver']:
                                                    df['Assign'][index] = Driver['Name']
                                                    Driver['First Deliver'] = df['deliveryTime'][index]
                                                    Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                    Driver['Cargo'] += df['Quantity'][index] 
                                                    assigned +=1
                                                    Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                    Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                    ##check if can load before
                                    elif df['timeBefore'][index] >= PSA_LOADING_TIME:
                                        
                                        ## try load before
                                        if ((Driver['Leave Port']+PSA_LOADING_TIME) <= df['QC Seq Time From'][index]) & (Driver['Leave Port'] >= df['ETB'][index]):
                                            
                                            df['deliveryTime'][index] = Driver['Leave Port']
                                            df['Assign'][index] = Driver['Name']
                                            Driver['Leave Port'] = df['deliveryTime'][index] + PSA_LOADING_TIME
                                            Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                            Driver['Cargo'] += df['Quantity'][index] 
                                            assigned +=1
                                        ##try load after & Check if possible to load after QC
                                        elif ((Driver['Leave Port'] + PSA_LOADING_TIME) <= df['ETU'][index]) & (df['timeAfter'][index] >= PSA_LOADING_TIME):
                                            
                                            if (Driver['Leave Port'] <= df['QC Seq Time To'][index]) :
                                                if ((df['QC Seq Time To'][index] + PSA_LOADING_TIME) <= Driver['End Work']):
                                                    df['deliveryTime'][index] = df['QC Seq Time To'][index]
                                                    df['Assign'][index] = Driver['Name']
                                                    Driver['Leave Port'] = df['deliveryTime'][index] + PSA_LOADING_TIME
                                                    Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                    Driver['Cargo'] += df['Quantity'][index] 
                                                    assigned +=1 
                                            else:
                                                if (Driver['Leave Port'] + PSA_LOADING_TIME) <= df['ETU'][index]:   
                                                    df['deliveryTime'][index] = Driver['Leave Port']
                                                    df['Assign'][index] = Driver['Name']
                                                    Driver['Leave Port'] = df['deliveryTime'][index] + PSA_LOADING_TIME
                                                    Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                    Driver['Cargo'] += df['Quantity'][index] 
                                                    assigned +=1 
                                        ## try shift timing to do after & Check if possible to load after QC
                                        elif (df['timeAfter'][index] >= PSA_LOADING_TIME) & ((Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS + TRAVEL_TIME + PSA_LOADING_TIME) <= df['ETU'][index])& ((Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS + TRAVEL_TIME + PSA_LOADING_TIME) <= Driver['First Deliver']) & (len(list(filter(lambda o: o['Type'] == 'Anchorage', Driver['Jobs']))) == 0):
                                            if ((Driver['First Deliver'] - PSA_LOADING_TIME) <= df['QC Seq Time To'][index]) :
                                                if ((df['QC Seq Time To'][index] + PSA_LOADING_TIME) <= df['ETU'][index]) & ((df['QC Seq Time To'][index] + PSA_LOADING_TIME) <= Driver['First Deliver']):
                                                    df['deliveryTime'][index] = df['QC Seq Time To'][index]
                                                    df['Assign'][index] = Driver['Name']
                                                    Driver['First Deliver'] = df['deliveryTime'][index]
                                                    Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                    Driver['Cargo'] += df['Quantity'][index] 
                                                    assigned +=1
                                                    Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                    Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                            elif (Driver['First Deliver'] - PSA_LOADING_TIME) >= df['QC Seq Time To'][index]:
                                                if (Driver['First Deliver'] - PSA_LOADING_TIME) <= df['ETU'][index]:
                                                    df['deliveryTime'][index] = Driver['First Deliver'] - PSA_LOADING_TIME
                                                    df['Assign'][index] = Driver['Name']
                                                    Driver['First Deliver'] = df['deliveryTime'][index]
                                                    Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                    Driver['Cargo'] += df['Quantity'][index] 
                                                    assigned +=1
                                                    Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                    Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                                else: 
                                                    if ((df['ETU'][index] - PSA_LOADING_TIME) >= (Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS + TRAVEL_TIME )):
                                                        df['deliveryTime'][index] = df['ETU'][index] - PSA_LOADING_TIME
                                                        df['Assign'][index] = Driver['Name']
                                                        Driver['First Deliver'] = df['deliveryTime'][index]
                                                        Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                        Driver['Cargo'] += df['Quantity'][index] 
                                                        assigned +=1
                                                        Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                        Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                        ## try shift timing to do before
                                        elif((Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS + TRAVEL_TIME + PSA_LOADING_TIME) <= df['QC Seq Time From'][index]) & ((Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS + TRAVEL_TIME + PSA_LOADING_TIME) <= Driver['First Deliver']) & (len(list(filter(lambda o: o['Type'] == 'Anchorage', Driver['Jobs']))) == 0):                        
                                            
                                            if df['QC Seq Time From'][index] <= Driver['First Deliver']:    
                                                df['deliveryTime'][index] = df['QC Seq Time From'][index] - PSA_LOADING_TIME
                                                df['Assign'][index] = Driver['Name']
                                                Driver['First Deliver'] = df['deliveryTime'][index]
                                                Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                Driver['Cargo'] += df['Quantity'][index] 
                                                assigned +=1
                                                Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                            else:
                                                if (Driver['First Deliver'] - PSA_LOADING_TIME) >= df['ETB'][index]:
                                                    df['deliveryTime'][index] = Driver['First Deliver'] - PSA_LOADING_TIME
                                                    df['Assign'][index] = Driver['Name']
                                                    Driver['First Deliver'] = df['deliveryTime'][index]
                                                    Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                    Driver['Cargo'] += df['Quantity'][index] 
                                                    assigned +=1
                                                    Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                    Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                        
                                        
                                    ##impossible to load before
                                    else:
                                        ##load after
                                        if (Driver['Leave Port'] + PSA_LOADING_TIME) <= df['ETU'][index]:
                                            if (Driver['Leave Port'] <= df['QC Seq Time To'][index]):
                                                if (df['QC Seq Time To'][index]+ PSA_LOADING_TIME) <= Driver['End Work']:
                                                    df['deliveryTime'][index] = df['QC Seq Time To'][index]
                                                    df['Assign'][index] = Driver['Name']
                                                    Driver['Leave Port'] = df['deliveryTime'][index] + PSA_LOADING_TIME
                                                    Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                    Driver['Cargo'] += df['Quantity'][index] 
                                                    assigned +=1 
                                            else:
                                                if (Driver['Leave Port'] + PSA_LOADING_TIME) <= df['ETU'][index]:
                                                    df['deliveryTime'][index] = Driver['Leave Port']
                                                    df['Assign'][index] = Driver['Name']
                                                    Driver['Leave Port'] = df['deliveryTime'][index] + PSA_LOADING_TIME
                                                    Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                    Driver['Cargo'] += df['Quantity'][index] 
                                                    assigned +=1 
                                        ## try shift timing to do after
                                        elif (Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS + TRAVEL_TIME + PSA_LOADING_TIME) <= df['ETU'][index]:
                                            ## Check got more than 2 hrs
                                            if (Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS + TRAVEL_TIME + PSA_LOADING_TIME) <= Driver['First Deliver']:
                                                ## Check if can shift
                                                if len(list(filter(lambda o: o['Type'] == 'Anchorage', Driver['Jobs']))) == 0:
                                                    if ((Driver['First Deliver'] - PSA_LOADING_TIME) <= df['QC Seq Time To'][index]) :
                                                        if ((df['QC Seq Time To'][index] + PSA_LOADING_TIME) <= df['ETU'][index]) & ((df['QC Seq Time To'][index] + PSA_LOADING_TIME) <= Driver['First Deliver']):
                                                            df['deliveryTime'][index] = df['QC Seq Time To'][index]
                                                            df['Assign'][index] = Driver['Name']
                                                            Driver['First Deliver'] = df['deliveryTime'][index]
                                                            Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                            Driver['Cargo'] += df['Quantity'][index] 
                                                            assigned +=1
                                                            Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                            Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                                    elif (Driver['First Deliver'] - PSA_LOADING_TIME) >= df['QC Seq Time To'][index]:
                                                        if (Driver['First Deliver'] - PSA_LOADING_TIME) <= df['ETU'][index]:
                                                            df['deliveryTime'][index] = Driver['First Deliver'] - PSA_LOADING_TIME
                                                            df['Assign'][index] = Driver['Name']
                                                            Driver['First Deliver'] = df['deliveryTime'][index]
                                                            Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                            Driver['Cargo'] += df['Quantity'][index] 
                                                            assigned +=1
                                                            Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                            Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                                        else: 
                                                            if ((df['ETU'][index] - PSA_LOADING_TIME) >= (Driver['Leave Port'] + TRAVEL_TIME - DRIVER_HOURS + TRAVEL_TIME )):
                                                                df['deliveryTime'][index] = df['ETU'][index] - PSA_LOADING_TIME
                                                                df['Assign'][index] = Driver['Name']
                                                                Driver['First Deliver'] = df['deliveryTime'][index]
                                                                Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                                                Driver['Cargo'] += df['Quantity'][index] 
                                                                assigned +=1
                                                                Driver['Leave Warehouse'] = Driver['First Deliver'] - TRAVEL_TIME
                                                                Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
    
            
            #If no Driver Available
            #Create new Driver
            driverIndex += 1
            Driver = {'Name':'Driver ' + str(driverIndex),
                    'First Deliver':None,
                    'Leave Warehouse':None,
                    'End Work':None,
                    'Leave Port':None,
                    'Cargo':0,
                    'Jobs':[],
                     }
            for index, row in df.iterrows():
                if df['Type'][index]=='Berthing':
                    ## Check if first delivery
                    if (df['Assign'][index] == 'Wait') :
                        if df['deliveryTime'][index] == None:
                            if df['timeBefore'][index] >= PSA_LOADING_TIME:
                                df['deliveryTime'][index] = df['QC Seq Time From'][index] - PSA_LOADING_TIME
                                firstDelivery = df['deliveryTime'][index]
                                Driver['First Deliver'] = firstDelivery
                                Driver['Leave Warehouse'] = firstDelivery - TRAVEL_TIME
                                Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                Driver['Leave Port'] = Driver["First Deliver"] + PSA_LOADING_TIME
                                df['Assign'][index] = Driver['Name']
                                Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                Driver['Cargo'] += df['Quantity'][index] 
                                assigned +=1
                                break
                            else:
                                df['deliveryTime'][index] = df['QC Seq Time To'][index]
                                firstDelivery = df['deliveryTime'][index]
                                Driver['First Deliver'] = firstDelivery
                                Driver['Leave Warehouse'] = firstDelivery - TRAVEL_TIME
                                Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                                Driver['Leave Port'] = Driver["First Deliver"] + PSA_LOADING_TIME
                                df['Assign'][index] = Driver['Name']
                                Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                                Driver['Cargo'] += df['Quantity'][index] 
                                assigned +=1
                                break
                        else:
                            firstDelivery = df['deliveryTime'][index]
                            Driver['First Deliver'] = firstDelivery
                            Driver['Leave Warehouse'] = firstDelivery - TRAVEL_TIME
                            Driver['End Work'] = Driver["Leave Warehouse"] + DRIVER_HOURS
                            Driver['Leave Port'] = Driver["First Deliver"] + PSA_LOADING_TIME
                            df['Assign'][index] = Driver['Name']
                            Driver['Jobs'].append({'Name':df['Vessel Name'][index], 'deliveryTime':df['deliveryTime'][index], 'Type':df['Type'][index]})
                            Driver['Cargo'] += df['Quantity'][index] 
                            assigned +=1
                            break
                            
            
            if Driver['Jobs']:
                drivers.append(Driver)

        ## Remove all crew time delay due to busy crew members
        for index, row in df.iterrows():
            df['ETB'][index] -= CREW_TIME
            
        df_driver=pd.DataFrame(drivers)
        return df_driver
    
    df_driver = assignDeliveryTime()
    return df_driver


if __name__ == "__main__":
    print(getDriverDetails(file))
