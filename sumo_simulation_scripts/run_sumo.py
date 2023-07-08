import os
import sys
import time
import json
import pandas as pd
import numpy as np
from sys import argv
from itertools import groupby
from xml.dom import minidom
from sim_utils_sumo import *
from multiprocessing import Process
import argparse


# conditional import, libsumo (if available) should be preferred as it is faster than traci
try:
    import libsumo as traci
except ImportError:
    import traci

import traci.constants as tc

print(traci)


# create the parser
parser = argparse.ArgumentParser()
init_arguments(parser)
args = parser.parse_args()
print(args)

print("TraffiCO2 version 2.03")

# simulation parameters
net_filename = args.net_file
route_filename = args.route_file
use_gui = True if int(args.gui) == 1 else False
opt_options = [] if len(args.sumo_opt) == 0 else args.sumo_opt.split(" ")


# save parameters
save_dir = args.save_dir
folder_prefix = args.prefix
create_log = True

#create simulation ID %d_%m_%H_%M_%S
sim_id = create_sim_id()

#create directory for output
save_dir=save_dir+folder_prefix+"_"+sim_id+"_"+str(np.random.randint(0, 1e9))
os.mkdir(save_dir)


# max steps in secs
max_steps = args.max_hours*60*60

# save v_edge every "sampling_freq" steps
sampling_freq = 5*60 # 5 minutes

#net_filename, route_filename = return_net_and_route_filenames(config_filename)
total_vehicles = return_number_vehicles(route_filename)

#configuration the simulation
def_options, opt_options, sumo_version = config_start_sumo(net_filename, route_filename, opt_options=opt_options, use_gui=use_gui)
print_starting_config(sim_id, use_gui, net_filename, route_filename, opt_options, total_vehicles, sumo_version, save_dir, max_steps)


#compute edge and vehicle list
edge_list = filter_edges_for_route(internal=True)
vehicle_id_list = return_vehicles_id(route_filename)

# measures to collect
collect_measures = prepare_dict_measures(args, save_dir, edge_list, vehicle_id_list)

print_recap_measures(collect_measures)


# simulation variables
n_teleports, step, vehicles_arrived = 0, 0, 0


# start time
start_t = time.time()


tmp = {}

while vehicles_arrived < total_vehicles and step < max_steps:

    vehicles_step = 0

    traci.simulationStep()
    vehicle_list = traci.vehicle.getIDList()

    # Subscriptions (only once when the vehicle enters the simulation)
    for veh_id in traci.simulation.getDepartedIDList():
        traci.vehicle.subscribe(veh_id, [tc.VAR_ROAD_ID, tc.VAR_CO2EMISSION, tc.VAR_POSITION, tc.VAR_SPEED, tc.VAR_NOXEMISSION, tc.VAR_FUELCONSUMPTION, tc.VAR_PMXEMISSION, tc.VAR_NOISEEMISSION, tc.VAR_HCEMISSION, tc.VAR_COEMISSION])


    for vehicle in vehicle_list:

        # get the results from the Subscription
        res_sub = traci.vehicle.getSubscriptionResults(vehicle)
        
        # update the data structure that collects the measures
        update_measures(vehicle, res_sub, collect_measures)
        
        # Vehicles per timestap
        if is_measure_to_collect(collect_measures, "v_step") and is_to_collect(vehicle, collect_measures["v_step"]["mode"]):
            vehicles_step += 1
    
        if is_measure_to_collect(collect_measures, "v_edge") and step%sampling_freq==0:
            edge_id = res_sub[tc.VAR_ROAD_ID]
            collect_measures["v_edge"]["values"]["edge"][edge_id][-1]+=1
            
    
    if is_measure_to_collect(collect_measures, "v_edge") and step%sampling_freq==0:    
        for k in collect_measures["v_edge"]["values"]["edge"]:
            collect_measures["v_edge"]["values"]["edge"][k].append(0)
    

    if is_measure_to_collect(collect_measures, "v_step"):
        collect_measures["v_step"]["values"]["vehicle"].append(vehicles_step)

    # collect number of teleported vehicles
    n_teleports += traci.simulation.getStartingTeleportNumber()

    step += 1
    vehicles_arrived += traci.simulation.getArrivedNumber()



elapsed = time.time() - start_t
print("END OF THE SIMULATION **********************")
print("Execution time (s): "+str(round(elapsed, 2)))
print("Number of teleports: "+str(n_teleports))


# Save measures
save_measures(collect_measures, edge_list, vehicle_id_list, save_dir)


# Create log file
if create_log:
    dict_log = {}
    dict_log["id"] = sim_id
    dict_log["sumo_version"] = sumo_version
    dict_log["net_filename"] = net_filename
    dict_log["route_filename"] = route_filename
    dict_log["def_options"] = def_options
    dict_log["opt_options"] = opt_options
    dict_log["execution_time_s"] = round(elapsed, 2)
    dict_log["n_vehicles"] = total_vehicles
    dict_log["n_teleports"] = n_teleports
    dict_log["n_steps"] = step
    dict_log["max_steps"] = max_steps

    a_file = open(save_dir+"/log.json", "w")
    json.dump(dict_log, a_file)
    a_file.close()

#close traci
traci.close()