import sumolib
from routing_utils import *
from utils import save_matrix
import json
from routing_algorithms import *
import os
import argparse
from tqdm import tqdm
import warnings


warnings.filterwarnings("ignore")


parser = argparse.ArgumentParser()

# Algorithm
parser.add_argument('-a', '--algorithm', required=True)
parser.add_argument('-k', type=int, required=True)


# Network and Demand
parser.add_argument('-n', '--net', required=True)
parser.add_argument('-d', '--demand', required=True)

parser.add_argument('-w', type=float, default=-1)
parser.add_argument('-p', type=float, default=-1)
parser.add_argument('-u', '--delta', type=float, default=-1)
parser.add_argument('-e', '--epsilon',  type=float, default=-1)
                 
# from to indices    
parser.add_argument('-f', required=True, type=int)
parser.add_argument('-t', required=True, type=int)

# output
parser.add_argument('-o', '--out', type=str, required=True)

     
args = parser.parse_args()
    

algorithm = args.algorithm
attribute = "traveltime"
ind_from = args.f
ind_to = args.t

tau = 1
  

save_path = args.out + "tmp/"
if not os.path.exists(save_path):
    os.makedirs(save_path, exist_ok=True)


# input paths
road_network_path = args.net
mobility_demand_path = args.demand

# Load the road network
road_network = sumolib.net.readNet(road_network_path, withInternal=False)
G = from_sumo_to_igraph_network(road_network)

# load the mobility demand
with open(mobility_demand_path) as json_file:
    dict_md = json.load(json_file)


if algorithm == "FASTEST":
    fun_to_apply = no_randomization
    fun_args = []
    
elif algorithm == "PP":
    fun_to_apply = path_penalization
    if args.k < 0 or args.p < 0:
        raise Exception(f"Wrong arguments for algorithm {algorithm}.") 
    fun_args = [args.k, args.p]
    
elif algorithm == "GR":
    fun_to_apply = graph_randomization
    if args.k < 0 or args.delta < 0:
        raise Exception(f"Wrong arguments for algorithm {algorithm}.") 
    fun_args = [args.k, args.delta, tau]
    
elif algorithm == "PR":
    fun_to_apply = path_randomization
    if args.k < 0 or args.delta < 0:
        raise Exception(f"Wrong arguments for algorithm {algorithm}.") 
    fun_args = [args.k, args.delta, tau]
    
elif algorithm == "KD":
    fun_to_apply = k_disjointed
    fun_args = [args.k]
    
elif algorithm == "DUA":
    fun_to_apply = duarouter
    if args.k < 0 or args.w < 0:
        raise Exception(f"Wrong arguments for algorithm {algorithm}.") 
    fun_args = [args.k, args.w]
    
elif algorithm == "KMDNSP":
    fun_to_apply = k_mdnsp
    if args.epsilon < 0:
        raise Exception(f"Wrong arguments for algorithm {algorithm}.") 
    fun_args = [args.epsilon]
    
elif algorithm == "PLATEAU":
    fun_to_apply = plateau_algorithm
    if args.epsilon < 1:
        raise Exception(f"Wrong arguments for algorithm {algorithm}.") 
    fun_args = [args.k, args.epsilon]    
    
    
    
matrix_name = f"tmp_matrix_{algorithm}_{ind_from}_{ind_to}.json"
dict_matrix = {}

if algorithm != "KMDNSP":
    

    for trip in tqdm(list(dict_md.keys())[ind_from: ind_to]):

        origin = dict_md.get(trip)["edges"][0]
        dest = dict_md.get(trip)["edges"][-1]
        
        if algorithm in ["GR", "PR", "DUA"]:
            result = fun_to_apply(G, origin, dest, *fun_args, attribute, max_iter=500)
        else:
            result = fun_to_apply(G, origin, dest, *fun_args, attribute)

        dict_matrix[trip] = result

    # save the results as a JSON
    save_matrix(dict_matrix, save_path+matrix_name, compress=False)

    
elif algorithm == "KMDNSP":
                    
    
    for trip in tqdm(list(dict_md.keys())[ind_from: ind_to]):

        origin = dict_md.get(trip)["edges"][0]
        dest = dict_md.get(trip)["edges"][-1]
        
        result = []
        k_tries = args.k
    
        while len(result)<=1 and k_tries>1:
    
            result = fun_to_apply(G, origin, dest, k_tries, *fun_args, attribute)
            k_tries-=1

            
        dict_matrix[trip] = result


    # save the results as a JSON
    save_matrix(dict_matrix, save_path+matrix_name, compress=False)

