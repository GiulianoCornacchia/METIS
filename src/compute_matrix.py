import subprocess
import argparse
import os
import json
from utils import save_matrix
import compress_json
from collections import ChainMap
import shutil


parser = argparse.ArgumentParser(
                    prog='ComputeSuggestionMatrix',
                    description='Compute Suggestions Matrices',
                    epilog='Text at the bottom of help')

# Algorithm
parser.add_argument('-a', '--algorithm', required=True)
parser.add_argument('-k', type=int, required=True)

# Network and Demand
parser.add_argument('-n', '--net', required=True)
parser.add_argument('-d', '--demand', required=True)
    

# baselines' arguments
parser.add_argument('-p', default=0)
parser.add_argument('-u', default=0)
parser.add_argument('-e', default=0)
parser.add_argument('-w', default=0)

# number of threads
parser.add_argument('-t', type=int, required=True)

# output
parser.add_argument('-o', '--out', type=str, required=True)

# identifier
parser.add_argument('-i', '--identifier', type=str, default="")

args = parser.parse_args()

str_p = str(args.p).replace(".","p")
str_d = str(args.u).replace(".","p")
str_e = str(args.e).replace(".","p")
str_w = str(args.w).replace(".","p")

city = args.identifier


if args.algorithm == "FASTEST":
    filename = f"matrix_{args.algorithm}_{city}.json"
elif args.algorithm == "PP":
    filename = f"matrix_{args.algorithm}_k{args.k}_p{str_p}_{city}.json"
elif args.algorithm in ["GR", "PR"]:
    filename = f"matrix_{args.algorithm}_k{args.k}_d{str_d}_{city}.json"
elif args.algorithm == "KD":
    filename = f"matrix_{args.algorithm}_k{args.k}_{city}.json"
elif args.algorithm == "DUA":
    filename = f"matrix_{args.algorithm}_k{args.k}_w{str_w}_{city}.json"
elif args.algorithm == "KMDNSP":
    filename = f"matrix_{args.algorithm}_k{args.k}_w{str_e}_{city}.json"
elif args.algorithm == "PLATEAU":
    filename = f"matrix_{args.algorithm}_k{args.k}_w{str_e}_{city}.json"


save_path = args.out
if not os.path.exists(save_path):
    os.makedirs(save_path, exist_ok=True)

                    
# load the mobility demand
mobility_demand_path = args.demand
with open(mobility_demand_path) as json_file:
    dict_md = json.load(json_file)
            
        
# compute the splits
N = len(dict_md)
s = args.t

step = N // s
splits = [(i * step, (i + 1) * step) for i in range(s)]
splits[-1] = (splits[-1][0], N)  # adjust last split to include any remaining values



                    
# Create subprocesses for each script and run them simultaneously
processes = []

for split in splits:
                    
    opts = f"-a {args.algorithm} -k {args.k} -n {args.net} -d {args.demand} -p {args.p} -u {args.u} -e {args.e} -w {args.w} -f {split[0]} -t {split[1]} -o {args.out}"
    
    command_list = ['python', "worker_matrix.py"]+opts.split(" ")
                    
    process = subprocess.Popen(command_list)
    processes.append(process)



# Wait for all subprocesses to complete
for process in processes:
    process.wait()

    
# Merge all the JSON

chunks_path = args.out + "tmp/"
chunks = [chunks_path+f for f in os.listdir(chunks_path)]
chunk_list = []

for chunk in chunks:
    data = compress_json.load(chunk)
    chunk_list.append(data)
    
merged_dict = dict(ChainMap(*chunk_list))

if len(merged_dict) == N:  
    save_matrix(merged_dict, save_path+filename, compress=False)
    print(f"Matrix {filename} saved!")
    
else:
    print("ERROR!!!")
    
# delete the tmp folder
shutil.rmtree(chunks_path)
    
# Print a message when all scripts are finished
print("All scripts have completed.")


