import os
import argparse
import subprocess


parser = argparse.ArgumentParser()

# demand and network
parser.add_argument('-n', '--net', type=str, required=True)
parser.add_argument('-r', '--route', type=str, required=True)
parser.add_argument('-o', "--out", type=str, default="./")
parser.add_argument('-s', "--sumopath", type=str, default="../sumo_simulation_scripts/")
parser.add_argument('-i', "--identifier", type=str, default="metis")


args = parser.parse_args()


# Path to the SUMO road network file
road_network_path = args.net

# Route file
route_file_path = args.route

# filename
name = args.identifier

# Output folder
output_folder = args.out
if not os.path.exists(output_folder):
    os.makedirs(output_folder, exist_ok=True)
    
    
# path to folder containing the sumo simulation script
path_sumo_script = args.sumopath


# SUMO options
opt =  '"-W --ignore-junction-blocker 20 --time-to-impatience 30 --time-to-teleport 120 --scale 1"'

s = f"-n {road_network_path} -r {route_file_path} -s {output_folder} --prefix {name}"

command_list = ['python', "run_sumo.py"]+s.split(" ")+["--sumo-opt", opt.replace('"',"")]

# Run command in the background
script = subprocess.Popen(command_list, cwd=path_sumo_script)

