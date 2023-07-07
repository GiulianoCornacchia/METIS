import compress_json
import pandas as pd
import json
from utils_metis import create_xml_vehicles

def save_matrix(matrix, filename, compress=True):
    
    if compress:
        compress_json.dump(matrix, filename+".gz")
    else:     
        with open(filename, "w") as a_file:
            json.dump(matrix, a_file)
            a_file.close()

            
def save_sumo_routes(final_paths, dict_md, save_path, name):

    dict_sumo = {}

    for trip_id in list(dict_md.keys()):

        route_trip_id = final_paths[trip_id]
        selected_path = route_trip_id[0]["edges"]
        new_id = name+"_"+trip_id.split("_")[1]
        dep_time = dict_md[trip_id]['time']

        dict_sumo[new_id] = {'edges':str(selected_path).replace(",","").replace("'","")[1:-1], 'time': dep_time}

    create_xml_vehicles(dict_sumo, f"{save_path}sumo_routes_{name}.rou.xml");
            
            
def prepare_dict_plot_measure(df, measure):

    dict_plot = {}

    for config in list(df.columns)[1:]:

        dict_plot[config] = {}

        for max_k in df["max_k"].unique():

            value_list = df[df["max_k"]==max_k][config].values[0][measure]

            dict_plot[config][max_k] = value_list

    return dict_plot


def prepare_dict_plot_one_k_measure(df, measure, k):

    dict_plot = {}

    for config in list(df.columns)[1:]:

        value_list = df[df["max_k"]==k][config].values[0][measure]

        dict_plot[config] = value_list
        
    dplot = pd.DataFrame(dict_plot).T
    dplot["y"] = dplot.values.tolist()
    dplot = dplot[["y"]].explode("y").reset_index().sort_values("index")

    return dplot

