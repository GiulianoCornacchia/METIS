import uuid
import random
import os
import sys
import xml
import pandas as pd
from datetime import datetime
import argparse
import sumolib
import numpy as np


# conditional import, libsumo (if available) should be preferred as it is faster than traci
try:
    import libsumo as traci
except ImportError:
    import traci
    
import traci.constants as tc


def prepare_dict_measures(args, save_dir, edge_list, vehicle_id_list):
    
    
    measure_2_details = {"gps":["vehicle"], 
                        "co2":["edge", "vehicle"],
                        "nox":["edge", "vehicle"],
                        "pmx":["edge", "vehicle"],
                        "noise":["edge", "vehicle"],
                         "hc":["edge", "vehicle"],
                         "co":["edge", "vehicle"],
                        "fuel":["edge", "vehicle"], 
                        "speed":["edge"], 
                        "traveltime":["vehicle"], 
                        "v_edge":["edge"], 
                        "v_step":["vehicle"]}
    
    collect_measures = {}
    
    # init the dict
    for measure in measure_2_details:
        
        collect_measures[measure] = {"mode": getattr(args, measure),#args[measure], 
                                     #"filenames": {k: f"{save_dir}/{measure}_{k}.csv" for k in measure_2_details[measure]},
                                     "values": {k: {} for k in measure_2_details[measure]}}
        
        
    # prepare the initial values 
    for measure in measure_2_details:
        
        if measure=="gps": 
            collect_measures["gps"]["values"]["uids"] = []
            collect_measures["gps"]["values"]["lats"] = []
            collect_measures["gps"]["values"]["lngs"] = []
            collect_measures["gps"]["values"]["timestamps"] = []
            
        elif measure in ["co2", "nox", "fuel", "hc", "co", "noise", "pmx"]:
            
            for edge in edge_list:
                collect_measures[measure]["values"]["edge"][edge] = 0
            for v_id in vehicle_id_list:
                collect_measures[measure]["values"]["vehicle"][v_id] = 0
                
        elif measure=="speed":
            for edge in edge_list:
                collect_measures[measure]["values"]["edge"][edge] = []
        
        elif measure=="traveltime":
            for v_id in vehicle_id_list:
                collect_measures[measure]["values"]["vehicle"][v_id] = 0 
                
        # Timeseries       
        elif measure=="v_edge":
            for edge in edge_list:
                collect_measures[measure]["values"]["edge"][edge] = [0]
                
        elif measure=="v_step":
            for v_id in vehicle_id_list:
                collect_measures[measure]["values"]["vehicle"] = []
        
    return collect_measures



def update_measures(vehicle, result_sub, collect_measures):
    
    # collect measures
    edge_id = result_sub[tc.VAR_ROAD_ID]
    x, y = result_sub[tc.VAR_POSITION]
    speed = result_sub[tc.VAR_SPEED]
    
    co2_emissions = result_sub[tc.VAR_CO2EMISSION]
    nox_emissions = result_sub[tc.VAR_NOXEMISSION]
    fuel_emissions = result_sub[tc.VAR_FUELCONSUMPTION]
    pmx_emissions = result_sub[tc.VAR_PMXEMISSION]
    hc_emissions = result_sub[tc.VAR_HCEMISSION]
    co_emissions = result_sub[tc.VAR_COEMISSION]
    noise_emissions = result_sub[tc.VAR_NOISEEMISSION]

    
    # updates the data structures
    
    # GPS
    if is_measure_to_collect(collect_measures, "gps") and is_to_collect(vehicle, collect_measures["gps"]["mode"]):

        lon, lat = traci.simulation.convertGeo(x, y)
        collect_measures["gps"]["values"]["uids"].append(vehicle)
        collect_measures["gps"]["values"]["lats"].append(lat)
        collect_measures["gps"]["values"]["lngs"].append(lon)
        collect_measures["gps"]["values"]["timestamps"].append(step)
        
    measures_edge_and_vehicle_level = ["co2", "nox", "fuel", "pmx", "noise", "co", "hc"]

    for m_ev in measures_edge_and_vehicle_level:
        
        if is_measure_to_collect(collect_measures, m_ev) and is_to_collect(vehicle, collect_measures[m_ev]["mode"]):
            
            m_ev_value = eval(m_ev+"_emissions")
                
            collect_measures[m_ev]["values"]["edge"][edge_id] += m_ev_value
            collect_measures[m_ev]["values"]["vehicle"][vehicle] += m_ev_value
              
        
    # Speed
    if is_measure_to_collect(collect_measures, "speed") and is_to_collect(vehicle, collect_measures["speed"]["mode"]):
        collect_measures["speed"]["values"]["edge"][edge_id].append(speed)
        
    
    # Traveltime
    if is_measure_to_collect(collect_measures, "traveltime") and is_to_collect(vehicle, collect_measures["traveltime"]["mode"]):
        collect_measures["traveltime"]["values"]["vehicle"][vehicle]+=1
    
    
    # Vehicles per edge (OLD but GOLD version)
   
    '''if is_measure_to_collect(collect_measures, "v_edge") and is_to_collect(vehicle, collect_measures["v_edge"]["mode"]):
        if len(collect_measures["v_edge"]["values"]["vehicle"][vehicle])>0:
            if collect_measures["v_edge"]["values"]["vehicle"][vehicle][-1]!=edge_id:
                collect_measures["v_edge"]["values"]["vehicle"][vehicle].append(edge_id)
        else:
            collect_measures["v_edge"]["values"]["vehicle"][vehicle] = [edge_id]'''

def is_measure_to_collect(collect_measures, measure):
    
    return collect_measures[measure]["mode"] != "none"


def init_arguments(parser):

    list_args = [
    {"names": ["-n", "--net-file"], "type": str, "required": True, "help": "Load road network description from FILE."},
    {"names": ["-r", "--route-file"], "type": str, "required": True, "help": "Load routes descriptions from FILE."},
    {"names": ["-g", "--gui"], "type": int, "required": False, "default":0, "help": "Whether to use the GUI (1) or not (0)."},
    {"names": ["-s", "--save-dir"], "type": str, "required": True, "help": "The path of the directory in which store the simulation results."},
    {"names": ["--max-hours"], "type": float, "required": False, "default":10, "help": "The maximum number of hours to simulate"},
    {"names": ["--prefix"], "type": str, "required": False, "default":"", "help": "The prefix to use for the output directory."},
    {"names": ["--co2"], "type": str, "required": False, "default":"real", "help": "Collection mode for CO2 emissions (mg/s) at edge/vehicle level: 'real' for all vehicles or 'none' for no vehicles."},
     {"names": ["--co"], "type": str, "required": False, "default":"none", "help": "Collection mode for CO emissions (mg/s) at edge/vehicle level: 'real' for all vehicles or 'none' for no vehicles."},
        {"names": ["--hc"], "type": str, "required": False, "default":"none", "help": "Collection mode for HC emissions (mg/s) at edge/vehicle level: 'real' for all vehicles or 'none' for no vehicles."},
    {"names": ["--nox"], "type": str, "required": False, "default":"none", "help": "Collection mode for NOx emissions (mg/s) at edge/vehicle level: 'real' for all vehicles or 'none' for no vehicles."},
        {"names": ["--pmx"], "type": str, "required": False, "default":"none", "help": "Collection mode for PMx emissions (mg/s) at edge/vehicle level: 'real' for all vehicles or 'none' for no vehicles."},
        {"names": ["--noise"], "type": str, "required": False, "default":"none", "help": "Collection mode for noise emissions (dBA/s) at edge/vehicle level: 'real' for all vehicles or 'none' for no vehicles."},
    {"names": ["--fuel"], "type": str, "required": False, "default":"real", "help": "Collection mode for fuel consumption (ml/s) at edge/vehicle level: 'real' for all vehicles or 'none' for no vehicles."},
    {"names": ["--traveltime"], "type": str, "required": False, "default":"real", "help": "Collection mode for the traveltime (s): 'real' for all vehicles or 'none' for no vehicles."},
    {"names": ["--speed"], "type": str, "required": False, "default":"none", "help": "Collection mode for speed (m/s) at edge/vehicle level: 'real' for all vehicles or 'none' for no vehicles."},
    {"names": ["--gps"], "type": str, "required": False, "default":"none", "help": "Collection mode for GPS traces: 'real' for all vehicles while 'none' for no vehicles."},
    {"names": ["--v-edge"], "type": str, "required": False, "default":"none", "help": "Collection mode for number of vehicles per edge: 'real' for all vehicles while 'none' for no vehicles."},
    {"names": ["--v-step"], "type": str, "required": False, "default":"none", "help": "Collection mode for number of vehicles per timestep: 'real' for all vehicles while 'none' for no vehicles."},
    {"names": ["--sumo-opt"], "type": str, "required": False, "default":"", "help": "Options with which to instantiate SUMO (see https://sumo.dlr.de/docs/sumo.html#options)."},
    ]




    for d in list_args:
        parser.add_argument(*d["names"], **({k: d[k] for k in d if k!="names"}))


def create_sim_id():

    now = datetime.now()
    dt_string = now.strftime("%d_%m_%H_%M_%S")

    return dt_string


def config_start_sumo(net_file, route_file, opt_options=[], use_gui=True):

    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("please declare environment variable 'SUMO_HOME'")

    #Configuration
    if use_gui:
        sumo_binary = os.environ['SUMO_HOME']+"/bin/sumo-gui" # sumo / sumo-gui
    else:
        sumo_binary = os.environ['SUMO_HOME']+"/bin/sumo" # sumo / sumo-gui


    '''
    When vehicles in SUMO are unable to move for some time they will be teleported to resolve dead-lock. 
    If this is not desired, sumo-option --ignore-junction-blocker <TIME> may be used to ignore vehicles which 
    are blocking the intersection on an intersecting lane after the specified time. 
    This can be used to model the real-life behavior of eventually finding a way around the offending 
    vehicle that is blocking the intersection.

    '''
    #def_options = [sumo_binary, "-c", config_file]

    def_options = [sumo_binary, "-n", net_file, "-r", route_file]

    options = def_options + opt_options

    #sumo_cmd = [sumo_binary, "-c", "./sumo_simulation_data/simple-sim.sumocfg"]"--time-to-teleport", 180  
    #sumo_cmd = [sumo_binary, "-c", config_file, "--ignore-junction-blocker", "30", "-W"]
    sumo_cmd = options
    #,"--no-internal-links", "True"]
    print(options)
    conn = traci.start(sumo_cmd)

    return def_options, opt_options, conn[1]


def return_number_vehicles(route_filename):

    route_xml = xml.dom.minidom.parse(route_filename)

    n_flows = len(route_xml.getElementsByTagName('flow'))
    n_vehicles = len(route_xml.getElementsByTagName('vehicle'))

    return n_flows+n_vehicles


def return_net_and_route_filenames(config_file):

    config_doc = xml.dom.minidom.parse(config_file)

    path_net = config_doc.getElementsByTagName('net-file')[0].attributes['value'].value
    path_route = config_doc.getElementsByTagName('route-files')[0].attributes['value'].value

    return path_net, path_route


def return_vehicles_id(route_file):

    route_xml = xml.dom.minidom.parse(route_file)
    id_list = [x.attributes["id"].value for x in route_xml.getElementsByTagName('vehicle')]

    return id_list

#Remember, the non-internal edges are the ones s.t. edge_id[0] != ":"
def filter_edges_for_route(internal=False):

    e_list = list(traci.edge.getIDList())

    if not internal:
        e_list = [e for e in e_list if e[0]!=":"]

    return e_list



def print_recap_measures(collect_measures):

    for m in collect_measures:
        print(f"{m}: {collect_measures[m]['mode']}")
    print("\n\n")




def save_measures(collect_measures, edge_list, vehicle_list, save_dir):
    
    # GPS
    if is_measure_to_collect(collect_measures, "gps"): 
        save_dataframe_gps(collect_measures)
            
    
    # EDGE-based measures as edge_id, measure_0, ... , measure_n
    measures_level = ["co2", "nox", "fuel", "pmx", "noise", "co", "hc"] # v_edge (removed since it can be inferred from mob demand)
    measures_to_save, colnames = [], [] 
    
    for measure in measures_level:    
        if is_measure_to_collect(collect_measures, measure):
            measures_to_save.append(measure)
            colnames.append(f"total_{measure}")
    
    save_dataframe_edges(collect_measures, edge_list, measures_to_save, colnames, f"{save_dir}/edge_measures.csv")
    
       
    # VEHICLE-based measures as edge_id, measure_0, ... , measure_n
    measures_level = ["co2", "nox", "fuel", "pmx", "noise", "co", "hc", "traveltime"]
    measures_to_save, colnames = [], [] 
    
    for measure in measures_level:    
        if is_measure_to_collect(collect_measures, measure):
            measures_to_save.append(measure)
            colnames.append(f"total_{measure}")
    
    save_dataframe_vehicles(collect_measures, vehicle_list, measures_to_save, colnames, f"{save_dir}/vehicle_measures.csv")
            
        
    # Vehicles for timestamp
    if is_measure_to_collect(collect_measures, "v_step"):

        d = pd.DataFrame()
        d["timestep"] = np.arange(len(collect_measures["v_step"]["values"]["vehicle"]))
        d["count_vehicles"] = collect_measures["v_step"]["values"]["vehicle"]

        d.to_csv(f"{save_dir}/v_step.csv", sep=",", index=False)    
    
    
    # Vehicles per edge
    if is_measure_to_collect(collect_measures, "v_edge"):
        
        # compute n_observations
        n_observations = len(collect_measures["v_edge"]["values"]["edge"][edge_list[0]])
                               
        list_columns = ["edge_id"] + [f"observation_{i+1}" for i in range(n_observations)]
        
        d = pd.DataFrame(columns=list_columns)
        
        d["edge_id"] = edge_list
        
        obs = {i:[] for i in range(n_observations)}
        
        for edge_id in collect_measures["v_edge"]["values"]["edge"]:
            
            obs_edge = collect_measures["v_edge"]["values"]["edge"][edge_id] 
            
            for j in range(len(obs_edge)):          
                obs[j].append(obs_edge[j])
            
        for i in range(len(obs)):
            d[f"observation_{i+1}"] = obs[i]
        
    
        d.to_csv(f"{save_dir}/v_per_edges.csv", sep=",", index=False) 
        
        
    '''
    
 
    # Speed
    if is_measure_to_collect(collect_measures, "speed"):
        save_dataframe_edges(collect_measures, "speed", "speed")
    '''
    
    # Vehicles per edge (old but gold)
    '''
    if is_measure_to_collect(collect_measures, "v_edge"):

        dict_final = {edge_id: 0 for edge_id in edge_list}
                
        for v in collect_measures["v_edge"]["values"]["vehicle"]:
            edges = collect_measures["v_edge"]["values"]["vehicle"][v]
            for e in edges:
                dict_final[e]+=1
                
        collect_measures["v_edge"]["values"]["edge"] = dict_final'''
    
    
        
        
def save_dataframe_gps(collect_measures):

    d_traces = pd.DataFrame()
    d_traces['uid'] = collect_measures["gps"]["values"]["uids"]
    d_traces['lat'] = collect_measures["gps"]["values"]["lats"]
    d_traces['lng'] = collect_measures["gps"]["values"]["lngs"]
    d_traces['timestamp'] = collect_measures["gps"]["values"]["timestamps"]

    d_traces.to_csv(collect_measures["gps"]["filenames"]["vehicle"], sep=",", index=False)
    

def save_dataframe_edges(collect_measures, edge_list, measures, col_names, filename):
    
    d_edge = pd.DataFrame()
    d_edge['edge_id'] = edge_list
    
    for ind, measure in enumerate(measures):
        list_values = []
        for edge_id in edge_list:
            list_values.append(collect_measures[measure]["values"]["edge"][edge_id])
            
        d_edge[col_names[ind]] = list_values
        
    d_edge.to_csv(filename, sep=",", index=False)


def save_dataframe_vehicles(collect_measures, vehicle_list, measures, col_names, filename):
    
    d_vehicle = pd.DataFrame()
    d_vehicle['vehicle_id'] = vehicle_list
    
    for ind, measure in enumerate(measures):
        list_values = []
        for v_id in vehicle_list:
            list_values.append(collect_measures[measure]["values"]["vehicle"][v_id])
            
        d_vehicle[col_names[ind]] = list_values
        
    d_vehicle.to_csv(filename, sep=",", index=False)



def create_df_veichles_time(list_n_vehicles):

    df = pd.DataFrame()
    df['n_vehicles'] = list_n_vehicles

    return df


def print_starting_config(sim_id, use_gui, net_filename, route_filename, opt_options, total_vehicles, sumo_version, save_dir, max_steps):

    print("\nSimulation id: "+sim_id)
    print("\nParameters: \n")
    print("Use GUI: "+str(use_gui))
    print("Network file: "+net_filename)
    print("Demand file: "+route_filename)
    print("SUMO options: "+str(opt_options))
    print("# vehicles to simulate: "+str(total_vehicles))
    print("Output Directory: "+save_dir)
    print("Max steps: "+str(max_steps))
    print("SUMO VERSION: "+sumo_version+"\n")
    print("<><><><><>") 


def is_to_collect(id_vehicle, collect_mode):

    if collect_mode == "all" or (collect_mode=="rand" and "background" in id_vehicle) or (collect_mode=="real" and not "background" in id_vehicle):
        return True
    else:
        return False