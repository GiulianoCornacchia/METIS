from tqdm.notebook import tqdm
import random
import igraph
import numpy as np
from routing_measures import *
from routing_utils import * 
from shapely.geometry import Polygon
from skmob.tessellation import tilers
import geopandas as gpd
import sumolib
import pandas as pd
import argparse
import xml
from xml.dom import minidom



def create_xml_vehicles(dict_vehicles, filename):
    
    # xml creation
    root = minidom.Document()
    xml = root.createElement("routes")
    xml.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    xml.setAttribute("xsi:noNamespaceSchemaLocation", "http://sumo.dlr.de/xsd/routes_file.xsd")
    root.appendChild(xml)

    #vehicle type(s)
    element = root.createElement("vType")
    element.setAttribute("id", "type1")
    element.setAttribute("accel", "2.6")
    element.setAttribute("decel", "4.5")
    element.setAttribute("sigma", "0.5")
    element.setAttribute("length", "5")
    element.setAttribute("maxSpeed", "70")
    xml.appendChild(element)

    valid_list = []
    invalid_list = []

    # sort the dict
    dict_vehicles_time_sorted = dict(sorted(dict_vehicles.items(), 
                                            key=lambda item: item[1]['time']))


    for traj_id in dict_vehicles_time_sorted.keys():

            edge_list = dict_vehicles_time_sorted[traj_id]['edges']

            valid_list.append(traj_id)

            start_second = str(dict_vehicles_time_sorted[traj_id]['time'])

            try:
                col = str(dict_vehicles_time_sorted[traj_id]['color'])
            except:
                col = "blue"
            
            element = root.createElement("vehicle")
            element.setAttribute("color", col)
            element.setAttribute("id", traj_id)
            element.setAttribute("type", "type1")
            element.setAttribute("depart", start_second)
            
            route_element = root.createElement("route")
            route_element.setAttribute("edges", edge_list)
            element.appendChild(route_element)

            xml.appendChild(element)

    xml_str = root.toprettyxml(indent="\t")

    with open(filename, "w") as f:
        f.write(xml_str)

    return {'valid':valid_list, 'invalid': invalid_list}

def parse_arguments():

    parser = argparse.ArgumentParser()

    # demand and network
    parser.add_argument('-d', '--demand', required=True)
    parser.add_argument('-n', '--net', required=True)

    # K-road and FLEP
    parser.add_argument('-t', '--tilesize', type=float, default=1000)
    parser.add_argument('-s', '--slowfactor', type=float, default=2)
    parser.add_argument('-p', type=float, default=0.01)
    parser.add_argument('-a', '--attribute', type=str, default="traveltime")

    # KMD
    parser.add_argument('-k', type=int, default=3)
    parser.add_argument('-e', '--eps', type=float, default=0.3)

    # other
    parser.add_argument('-o', "--out", type=str, required=True, default="./")
    parser.add_argument('-i', '--identifier', type=str, default="metis")

    # PARSE THE ARGUMENTS

    args = parser.parse_args()
    
    return args


def __create_dict_edge_tile(road_network, tessellation, exclude_roundabouts=False):
    
    lng_list, lat_list, edge_id_list = [], [], []

    edges_in_roundabouts = []

    if exclude_roundabouts:
        for r in road_network.getRoundabouts():
            for e in r.getEdges():
                edges_in_roundabouts.append(e)
    
    for edge in road_network.getEdges():

        edge_id = edge.getID()

        if edge_id not in edges_in_roundabouts:

            lng, lat = gps_coordinate_of_edge(road_network, edge_id)

            edge_id_list.append(edge_id)
            lng_list.append(lng)
            lat_list.append(lat)


    edge_coords = gpd.points_from_xy(lng_list, lat_list)
    
    gpd_edges = gpd.GeoDataFrame(geometry=edge_coords)
    gpd_edges['edge_ID'] = edge_id_list
    
    sj = gpd.sjoin(tessellation, gpd_edges)
    sj = sj.drop(["index_right", "geometry"], axis=1)
    
    return {edge_id: tile_id for tile_id, edge_id in zip(sj["tile_ID"], sj["edge_ID"])}



def gps_coordinate_of_edge(net, edge_id):

    x, y = net.getEdge(edge_id).getFromNode().getCoord()
    lon, lat = net.convertXY2LonLat(x, y)

    return lon, lat



def estimate_k_road(G, dict_md, n_samples, attribute, dict_edge_tile, threshold=0.8, origin=True):
    
    dict_estimated_paths = {}
    
    # estimate the path (fastest path on the perturbed graph) and compute k_road
    for trip_id in tqdm(list(dict_md.keys())):

        from_edge = dict_md.get(trip_id)["edges"][0]
        to_edge = dict_md.get(trip_id)["edges"][-1]

        paths_pp_estimate = get_shortest_path(G, from_edge, to_edge, attribute)
        dict_estimated_paths[trip_id] = paths_pp_estimate["sumo"]


    ds = compute_driver_sources(list(dict_estimated_paths.values()), dict_edge_tile, origin=origin)
    mds = compute_MDS(ds, threshold)
    k_road_estimated = compute_k_road(mds)

    
    return k_road_estimated



def compute_dict_edge_to_tile(road_network, tile_size):
    
    bbox_xy = road_network.getBBoxXY()
    corner1 = road_network.convertXY2LonLat(*bbox_xy[0])
    corner2 = road_network.convertXY2LonLat(*bbox_xy[1])
    polygon = Polygon([corner1, (corner2[0], corner1[1]), corner2, (corner1[0], corner2[1])])

    # Create a GeoDataFrame with a single row containing the polygon
    data = {'geometry': [polygon]}
    gdf = gpd.GeoDataFrame(data)
    tessellation_gdf = gpd.GeoDataFrame(gdf, crs="EPSG:4326")
    
    tessellation = tilers.tiler.get("squared", base_shape=tessellation_gdf, meters=tile_size)
    
    dict_edge_tile = __create_dict_edge_tile(road_network, tessellation, exclude_roundabouts=True)
    
    return dict_edge_tile



def create_df_mobility_demand(dict_md):
    
    dict_df = {}
    
    for vid in dict_md:

        edge_from = dict_md[vid]["edges"][0]
        edge_to = dict_md[vid]["edges"][-1]
        time = dict_md[vid]["time"]
        dict_df[vid]={"edge_from": edge_from, "edge_to": edge_to, "time":time}  
        
    df = pd.DataFrame(dict_df).T.reset_index().rename(columns={"index":"trip_id"})
    df = df.sort_values("time")
    
    return df

