import sumolib
import json
from routing_algorithms import k_mdnsp
import numpy as np
from tqdm import tqdm
from utils import save_matrix, save_sumo_routes
from numpy.random import choice
import random
from utils_metis import *

import warnings
warnings.filterwarnings("ignore")


'''
METIS 

'''


def FLEP(G, dict_time_penalty, attribute, time, previous_timestamp, p_trip, slow_factor): 
    
    """
    Apply the Forward-Looking Edge Penalization (FLEP) to the graph G.

    Args:
        G (igraph.Graph): Input graph.
        dict_time_penalty (dict): Dictionary containing penalized edges for each timestamp.
        attribute (str): Attribute name in the graph representing the edge property.
        time (int): Current timestamp.
        previous_timestamp (int): Previous timestamp.
        p_trip (float): Trip penalization factor.

    Returns:
        None
    """

    
    if previous_timestamp != time:

        # apply penalization counting only trip already started
        dict_departed = {time_k: dict_time_penalty[time_k] for time_k in dict_time_penalty if time_k < time}

        G.es[f"tmp_{attribute}"] = G.es[attribute] 

        for t in dict_departed:

            time_budget = time-t

            for path_departed_t in dict_departed[t]:

                ig_id_list = [G["edge_sumo_ig"][e] for e in path_departed_t]
                list_tt = G.es[ig_id_list][attribute]

                cum_sum_tt = np.cumsum(list_tt)                                      
                cum_sum_tt_slow = cum_sum_tt*slow_factor

                if time_budget>=cum_sum_tt_slow[-1]:
                    index_first_edge = len(cum_sum_tt_slow)
                elif time_budget<cum_sum_tt_slow[0]:
                    index_first_edge = 0
                else:
                    index_first_edge = np.argmin(cum_sum_tt_slow <= time_budget)

                edges_2_penalize = path_departed_t[index_first_edge:]

                # penalize only the "reachable" edges
                for e in edges_2_penalize:
                    G.es[G["edge_sumo_ig"][e]][f"tmp_{attribute}"] *= (1+p_trip)

                    

def route_selection(paths_mdnsp, k_road_source_estimated, k_road_dest_estimated, dict_edge_length, dict_edge_capacity):
    
    """
    Select the route that minimizes the route scoring function.

    Args:
        paths_mdnsp (list): List of candidate paths.
        k_road_source_estimated (dict): Estimated k-road source values for each edge.
        k_road_dest_estimated (dict): Estimated k-road destination values for each edge.
        dict_edge_length (dict): Dictionary mapping edge IDs to their lengths.
        dict_edge_capacity (dict): Dictionary mapping edge IDs to their capacities.

    Returns:
        dict: Selected path with the minimum score.
    """
    
    paths_kroad_source = []
    paths_kroad_dest = []
    paths_capacity = []
    paths_measure = []

    # compute the weighted average of the k-road based on the road length
    for path in paths_mdnsp:

        edge_list = path["edges"]

        # k-road
        vector_kroad_source = [k_road_source_estimated.get(e, 0.01) for e in edge_list]
        vector_kroad_dest = [k_road_dest_estimated.get(e, 0.01) for e in edge_list]

        vector_length = [dict_edge_length.get(e) for e in edge_list]
        vector_capacity = [dict_edge_capacity.get(e) for e in edge_list]

        avg_kroad_source = np.average(vector_kroad_source, weights=vector_length)
        avg_kroad_dest = np.average(vector_kroad_dest, weights=vector_length)

        avg_capacity = np.average(vector_capacity, weights=vector_length)

        measure = (avg_kroad_source*avg_kroad_dest)/avg_capacity

        paths_kroad_source.append(avg_kroad_source)
        paths_kroad_dest.append(avg_kroad_dest)
        paths_capacity.append(avg_capacity)

        paths_measure.append(measure)

    # select a path with the min score
    index_choice = np.argmin(paths_measure)

    selected_path = paths_mdnsp[index_choice]

    return selected_path 
                        
                        

        

def METIS():

    # PARSE THE ARGUMENTS
    args = parse_arguments()


    # Path to the file containing the mobility demand
    mobility_demand_path = args.demand

    # Path to the SUMO road network file
    road_network_path = args.net

    # Tile size used for partitioning the road network (in meters)
    tile_size = args.tilesize

    # Slowdown parameter used in the FLEP algorithm
    slow_factor = args.slowfactor

    # Penalization factor used in the FLEP algorithm    
    p_trip = args.p

    # Name of the attribute representing the edge property in the graph
    attribute = args.attribute

    # Number of candidates generated using KMD (KMDNSP)
    k = args.k

    # Epsilon value used in the KMD algorithm
    epsilon = args.eps

    # Output directory path to save the results
    save_path = args.out

    # Identifier for the output files.    
    name = args.identifier


    # load the SUMO road network
    road_network = sumolib.net.readNet(road_network_path, withInternal=False)

    # load the mobility demand
    with open(mobility_demand_path) as json_file:
        dict_md = json.load(json_file)


    # compute the dict edge 2 tile
    dict_edge_tile = compute_dict_edge_to_tile(road_network, tile_size)

    # create a DataFrame describing the mobility demand
    df = create_df_mobility_demand(dict_md)

    # compute the total number of trips (vehicles)
    tot_vehicles = len(dict_md)

    # Convert the sumo network into an Igraph network
    G = from_sumo_to_igraph_network(road_network)
    sumo_to_ig = {e["id"] : e.index for e in G.es()}

    # compute edge capacity
    dict_edge_capacity = compute_edge_capacity(road_network.getEdges())

    # compute dict edge length
    dict_edge_length = {e.getID(): e.getLength() for e in road_network.getEdges()}

    # Estimate K-road source
    k_road_source_estimated = estimate_k_road(G, dict_md, len(dict_md), "traveltime", dict_edge_tile, threshold=0.8, origin=True)

    # Estimate K-road dest
    k_road_dest_estimated = estimate_k_road(G, dict_md, len(dict_md), "traveltime", dict_edge_tile, threshold=0.8, origin=False)

    # create a copy of the attribute
    G.es[f"tmp_{attribute}"] = G.es[attribute] 


    # set of final routes
    final_paths = {}

    # dict_time_penalty is used for the Forward-Looking Edge Penalization (FLEP)
    dict_time_penalty = {}
    dict_md_sorted = {k: dict_md[k] for k in df["trip_id"].values}

    previous_timestamp = -1

    for trip_id in tqdm(list(dict_md_sorted.keys())):

        edge_from = dict_md[trip_id]["edges"][0]
        edge_to = dict_md[trip_id]["edges"][-1]
        time = int(dict_md[trip_id]["time"])

        # Apply the Forward-Looking Edge Penalization (FLEP)
        FLEP(G, dict_time_penalty, attribute, time, previous_timestamp, p_trip, slow_factor)

        # Generate 𝑘 candidates on the penalized road network using KMD (KMDNSP)
        paths_mdnsp = k_mdnsp(G, edge_from, edge_to, k, epsilon, f"tmp_{attribute}")

        # Select the route that minimizes the route scoring function
        selected_path = route_selection(paths_mdnsp, k_road_source_estimated, k_road_dest_estimated, dict_edge_length, dict_edge_capacity)

        # Update the assigned routes collection
        final_paths[trip_id] = [selected_path]

        # store the assigned paths for this time slot
        if time not in dict_time_penalty:
            dict_time_penalty[time] = []

        dict_time_penalty[time].append(selected_path["edges"])

        # penalize only the starting edge for the current time-stamp
        e = selected_path["edges"][0]
        G.es[G["edge_sumo_ig"][e]][f"tmp_{attribute}"] *= (1+p_trip)

        previous_timestamp = time



    matrix_name = f"matrix_{name}.json"

    if save_path[-1] != "/":
        save_path = save_path + "/"

    # save the results as a JSON
    save_matrix(final_paths, save_path+matrix_name, compress=False)

    # save the result as a .rou file to be used in SUMO
    save_sumo_routes(final_paths, dict_md, save_path, name)

    
    
def main():
    METIS()
    
    
if __name__ == "__main__":
    main() 
