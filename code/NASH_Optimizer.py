# #############################################################################
# ####### GREEN-PRESSURE - EMISSION-REDUCING SIGNALIZED INTERSECTION MANAGEMENT
# #######
# #######     AUTHOR:       Kevin Riehl <kriehl@ethz.ch> 
# #######     YEAR :        2025
# #######     ORGANIZATION: Traffic Engineering Group (SVT), 
# #######                   Institute for Transportation Planning and Systems,
# #######                   ETH Zürich
# #############################################################################
"""
This code will run multiple microsimulation with the Green-Pressure
signal controller to optimize the weights using NASH optimization algorithm.
"""




# *****************************************************************************
# ******* IMPORTS *************************************************************
# *****************************************************************************
import pandas as pd
import numpy as np
import subprocess
import sys
import random
from concurrent.futures import ThreadPoolExecutor
import os
import ast




# *****************************************************************************
# ******* METHODS *************************************************************
# *****************************************************************************
def determineEmissions(folder="../model/logs"):
    f = open(folder+"/"+"Emissions.xml", "r")
    content = f.read()
    f.close()
    lines = content.split("\n")
    lines = [line.strip() for line in lines]
    emissions = []
    for l_ctr in range(0, len(lines)):
        line = lines[l_ctr]
        if line.startswith("<timestep "):
            time = line.split("\"")[1].split("\"")[0]
            relevant_lines = []
            for l_ctr2 in range(l_ctr+1, len(lines)):
                line = lines[l_ctr2]
                if line.startswith("</timestep>"):
                    break
                else:
                    relevant_lines.append(line)
            co2 = 0
            co  = 0
            hc  = 0
            NOx = 0
            PMx = 0
            for line in relevant_lines:
                co2 += float(line.split("CO2=\"")[1].split("\"")[0])
                co  += float(line.split("CO=\"")[1].split("\"")[0])
                hc  += float(line.split("HC=\"")[1].split("\"")[0])
                NOx += float(line.split("NOx=\"")[1].split("\"")[0])
                PMx += float(line.split("PMx=\"")[1].split("\"")[0])
            emissions.append([time, co2, co, hc, NOx, PMx])
    df_emissions = pd.DataFrame(emissions, columns=["time", "co2", "co", "hc", "NOx", "PMx"])
    df_emissions["goal"] = df_emissions["co2"]*0.15 + df_emissions["co"]*0.10 + df_emissions["hc"]*0.15 + df_emissions["NOx"]*0.30 + df_emissions["PMx"]*0.30
    total_emissions = sum(df_emissions["goal"])
    return total_emissions, df_emissions

# Define the function to run the simulation
def run_simulation(candidate_weights):
    script_name = "RunSimulation_green_pressure.py"
    arguments = ["--sumo-path", SUMO_PATH, "--controller", "GREEN_PRESSURE", "--weights", str(candidate_weights).replace(" ", "").replace("[","").replace("]","")]
    result = subprocess.run(["python", script_name] + arguments, capture_output=True, text=True)
    print("FINISHED RUNNING", result.stdout, result.stderr)
    return result.stdout, result.stderr  

def logProcess(iteration, new_best, candidate_weights, candidate_score, std):
    f = open("nash_optim_log.txt", "a+")
    f.write(str(iteration))
    f.write("\t")
    f.write(str(new_best))
    f.write("\t")
    f.write(str(candidate_score))
    f.write("\t")
    f.write(str(candidate_weights).replace(" ",""))
    f.write("\n")
    f.close()

def loadLastOptim():
    f = open("nash_optim_log.txt", "r")
    content = f.read()
    f.close()
    lines = content.split("\n")
    best_score = INIT_SCORE
    best_weights = INIT_WEIGHTS
    for line in lines:
        try:
            weights = ast.literal_eval(line.split("\t")[3].replace("\n", ""))
            score = float(line.split("\t")[2])
            if line.split("\t")[1]=="True":
                if score<best_score:
                    best_score = score
                    best_weights = weights
        except:
            pass
    return best_weights, best_score




# *****************************************************************************
# ******* MAIN ****************************************************************
# *****************************************************************************
SUMO_PATH = "C:/Users/kriehl/AppData/Local/sumo-1.19.0/bin/sumo-gui.exe"
INIT_WEIGHTS = [1,1,1,1,1]
INIT_SCORE = 1000000000000000000
NUM_ITERATIONS = 1000  # Number of iterations to try
SEARCH_RADIUS = 0.08

# Check if Optim Log Exists
if os.path.exists("nash_optim_log.txt"):
    best_weights, best_score = loadLastOptim()
    print(f"Initial Solution 0: {best_weights} with score {best_score}")
else:
    best_weights = INIT_WEIGHTS
    run_simulation(best_weights)
    score, std = determineEmissions()
    best_score = score
    print(f"Initial Solution 0: {best_weights} with score {best_score}")
    logProcess(-1, True, best_weights, score, std)
    
# NASH-optimization
# Min. Optimization loop
for i in range(NUM_ITERATIONS):
    # Generate new candidate weights by slightly modifying the current best weights
    candidate_weights = [w + random.uniform(-SEARCH_RADIUS, SEARCH_RADIUS) for w in best_weights]  # Add small random perturbations
    candidate_weights = [w if w >= 0 else 0 for w in candidate_weights]
    candidate_weights = [w / candidate_weights[0] for w in candidate_weights]
    # Run simulation
    run_simulation(candidate_weights)
    # Evaluate the candidate weights
    candidate_score, std = determineEmissions()
    print("\t", "Candidate", candidate_score, "["+str(std)+"]")
    # If the candidate is better, update the best weights and efficiency
    if candidate_score < best_score:  # Assuming lower efficiency is better
        best_weights = candidate_weights[:]
        best_score = candidate_score
        print(f"New best found at iteration {i}: {best_weights} with efficiency {best_score}")
        logProcess(i, True, best_weights, best_score, std)
    else:
        print(f"Wasted iteration iteration {i}: {candidate_weights} with efficiency {candidate_score}")
        logProcess(i, False, candidate_weights, candidate_score, std)
