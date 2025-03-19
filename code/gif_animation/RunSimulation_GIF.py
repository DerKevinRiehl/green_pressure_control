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
This code will run a microsimulation with the Green-Pressure
signal controller and generate relevant log files.
"""




# #############################################################################
# ## IMPORTS
# #############################################################################
import os
import sys
import traci
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import warnings
if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
warnings.filterwarnings("ignore")




# #############################################################################
# ## RUN ARGUMENTS & PARSING
# #############################################################################

sumoBinary = "C:/Users/kriehl/AppData/Local/sumo-1.19.0/bin/sumo-gui.exe"
CONTROL_MODE = "GREEN_PRESSURE" # FIXED_CYCLE, MAX_PRESSURE, GREEN_PRESSURE




# #############################################################################
# ## PARAMETERS
# #############################################################################

# SIMULATION PARAMETER
    # TIME PARAMETER
SIMULATION_STEPS_PER_SECOND = 4
SIMULATION_WAIT_TIME = 0
start_time = datetime.strptime("2024-03-04 09:15:00", "%Y-%m-%d %H:%M:%S")
end_time = datetime.strptime("2024-03-04 23:00:00", "%Y-%m-%d %H:%M:%S")
simulation_times = [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in [start_time + timedelta(seconds=i) for i in range(int((end_time - start_time).total_seconds()) + 1)]]
    # PUBLIC TRANSPORT PARAMETER
BUS_STOP_DURATION = 20 # SECS
    # SIGNAL CONTROL PARAMETER
T_A = 5
T_L = 3
G_T_MIN = 5
G_T_MAX = 50
WEIGHTS_MAX_PRESSURE = {"car": 1.0, "moc": 1.0, "lwt": 1.0, "hwt": 1.0, "bus": 1.0}
WEIGHTS_GREEN_PRESSURE = {"car": 1.0, "moc": 0.61, "lwt": 1.12, "hwt": 5.73, "bus": 13.19}

    # DEBUGGING
DEBUG_CONTROLLER_LOG = "NONE"# "intersection2"
DEBUG_SPAWN_LOG = False
DEBUG_TIME = True
DEBUG_GUI = False




# #############################################################################
# ## METHODS
# #############################################################################

def loadEmissionClassesFromFile(file="../data/Emission_VehiclePopulation.xlsx"):
    df_emissions_car = pd.read_excel(file, sheet_name="hb_passenger_car")
    df_emissions_moc = pd.read_excel(file, sheet_name="hb_motor_cycle")
    df_emissions_lwt = pd.read_excel(file, sheet_name="hb_transporter")
    df_emissions_hwt = pd.read_excel(file, sheet_name="hb_truck")
    df_emissions_bus = pd.read_excel(file, sheet_name="hb_bus")
    rel_columns = ["fleet_share_2022", "sumo_emission_class"]
    df_emissions_car = df_emissions_car[rel_columns]
    df_emissions_moc = df_emissions_moc[rel_columns]
    df_emissions_lwt = df_emissions_lwt[rel_columns]
    df_emissions_hwt = df_emissions_hwt[rel_columns]
    df_emissions_bus = df_emissions_bus[rel_columns]
    emission_model = {"car": df_emissions_car, 
                      "moc": df_emissions_moc, 
                      "lwt": df_emissions_lwt, 
                      "hwt": df_emissions_hwt, 
                      "bus": df_emissions_bus}
    return emission_model   

def getRandomEmissionClass(vehicle_class, emission_model):    
    probs = [v for v in emission_model[vehicle_class]["fleet_share_2022"]]
    probs = [p/sum(probs) for p in probs]
    vals  = ["HBEFA4/"+v for v in emission_model[vehicle_class]["sumo_emission_class"]]
    random_emission_class = np.random.choice(vals, size=1, p=probs)[0]
    return random_emission_class

def getRandomVehicleClass(no_truck=False):
    probs = [0.81, 0.082, 0.046, 0.062]
    vals = ["car", "moc", "lwt", "hwt"]
    random_vehicle_class = np.random.choice(vals, size=1, p=probs)[0]
    while no_truck and random_vehicle_class=="hwt":
        random_vehicle_class = np.random.choice(vals, size=1, p=probs)[0]
    return random_vehicle_class

def determineWhetherTruckBannedRoute(desired_route):
    route_entrance = desired_route.split("_")[1]
    route_exit = desired_route.split("_")[2]
    selected_entrances = ["E21", "E22", "E24", "E25", "E20", "E3", "E4", "E5", "E1", "E2", "E6", "E7", "E12", "E13"]
    selected_exits = ["A1", "A2", "A3", "A16", "A18", "A15"]
    if route_entrance in selected_entrances and route_exit in selected_exits:
        return False
    return True

sumo_vehicle_types = {
    "car": "sumo_car",
    "moc": "sumo_motorcycle",
    "lwt": "sumo_transporter",
    "hwt": "sumo_truck",
    "bus": "sumo_bus",
}

def spawnRandomVehicle(veh_ctr, desired_route):
    # determine vehicle characteristics
    new_vehicle_id = "VEH_"+str(veh_ctr)
    no_truck = determineWhetherTruckBannedRoute(desired_route)
    vehicle_class = getRandomVehicleClass(no_truck)
    emission_class = getRandomEmissionClass(vehicle_class, emission_model)
    vehicle_type = sumo_vehicle_types[vehicle_class]
    # add vehicle with traci
    traci.vehicle.add(new_vehicle_id, desired_route, typeID=vehicle_type)
    traci.vehicle.setEmissionClass(new_vehicle_id, emission_class)
    if DEBUG_SPAWN_LOG:
        print(new_vehicle_id, no_truck, vehicle_class, emission_class, vehicle_type)
    veh_routes[new_vehicle_id] = desired_route
    veh_classes[new_vehicle_id] = vehicle_class
    
def spawnRandomBus(veh_ctr, desired_route, stops):
    # determine vehicle characteristics
    new_vehicle_id = "BUS_"+str(veh_ctr)+"-"+desired_route
    vehicle_class = "bus"
    emission_class = getRandomEmissionClass(vehicle_class, emission_model)
    vehicle_type = sumo_vehicle_types[vehicle_class]
    # add vehicle with traci
    traci.vehicle.add(new_vehicle_id, desired_route, typeID=vehicle_type)
    traci.vehicle.setEmissionClass(new_vehicle_id, emission_class)
    for stop in stops.split("-"):
        traci.vehicle.setBusStop(new_vehicle_id, stop, duration=BUS_STOP_DURATION)    
    if DEBUG_SPAWN_LOG:
        print(new_vehicle_id, False, vehicle_class, emission_class, vehicle_type)
    veh_routes[new_vehicle_id] = desired_route
    veh_classes[new_vehicle_id] = vehicle_class

def determine_current_state():
    current_vehicles = traci.vehicle.getIDList()
    if len(current_vehicles)==0:
        print(">> NOTHING, so no state")
        return None, None
    current_lanes = [traci.vehicle.getLaneID(v_id) for v_id in current_vehicles]
    new_current_lanes = []
    for v_ctr in range(0, len(current_vehicles)):
        if not current_lanes[v_ctr].startswith(":"):
            new_current_lanes.append(current_lanes[v_ctr])
        else:
            v_id = current_vehicles[v_ctr]
            v_route = traci.vehicle.getRoute(v_id)
            v_current_edge_index = traci.vehicle.getRouteIndex(v_id)
            v_current_edge = v_route[v_current_edge_index]
            new_current_lanes.append("@"+v_current_edge)
    df_current_status = pd.DataFrame(np.asarray([current_vehicles, new_current_lanes]).transpose(), columns=["veh_id", "lane"])
    df_current_status["class"] = df_current_status["veh_id"].map(veh_classes)
    if CONTROL_MODE=="MAX_PRESSURE":
        df_current_status["weight"] = df_current_status["class"].map(WEIGHTS_MAX_PRESSURE)
    else:
        df_current_status["weight"] = df_current_status["class"].map(WEIGHTS_GREEN_PRESSURE)
    df_hidden_vehicles = df_current_status[df_current_status["lane"].str.startswith("@")]
    df_hidden_vehicles["edge"] = df_hidden_vehicles["lane"].str.replace("@","")
    return df_current_status, df_hidden_vehicles

class SignalController:
    def __init__(self, intersection_name, phases, links, multiplier=None):
        self.intersection_name = intersection_name
        self.phases = phases
        self.links = links
        self.current_gt_start = 0
        self.current_phase = self.phases[0]
        self.next_phase = -1
        self.current_state = "start"
        self.timer = -1
        self.pressures = []
        self.multiplier = multiplier
        
    def doSignalLogic(self):
        self.timer += 1
        self.determinePressures()
        if self.intersection_name==DEBUG_CONTROLLER_LOG:
            print("")
            print(self.current_state, self.timer, "State:", self.current_phase, self.pressures, traci.simulation.getTime()-self.current_gt_start)
        if self.current_state == "start":
            if self.timer==G_T_MIN:
                self.current_state="check_pressures"
                self.timer = -1
            else:
                pass
        elif self.current_state=="check_pressures":
            current_pressure = self.pressures[int(self.current_phase/2)]
            other_pressures = max(self.pressures)
            if current_pressure < other_pressures:
                self.current_state="next_phase"
                self.timer = -1
            else:
                self.current_state="wait"
                self.timer = -1
        elif self.current_state=="wait":
            if self.timer==T_A:
                current_gt = traci.simulation.getTime()-self.current_gt_start
                if current_gt > G_T_MAX:
                    self.current_state = "next_phase"
                    self.timer = -1
                else:
                    self.current_state="check_pressures"
                    self.timer = -1
            else:
                pass
        elif self.current_state=="next_phase":
            valid_indices = [i for i in range(len(self.pressures)) if i != int(self.current_phase/2)]
            max_pressure = max(self.pressures[i] for i in valid_indices)
            max_indices = [i for i in valid_indices if self.pressures[i] == max_pressure]
            self.next_phase = int(random.choice(max_indices)*2)
            self.current_phase += 1
            if self.intersection_name==DEBUG_CONTROLLER_LOG:
                print(">>\t", self.current_phase, max_pressure, max_indices, valid_indices, self.current_phase, self.next_phase)
            self.timer = -1
            self.current_state="transition"
        elif self.current_state=="transition":
            if self.timer==T_L:
                self.current_phase = self.next_phase 
                self.next_phase = -1
                self.timer = -1
                self.current_state = "start"
                self.current_gt_start = traci.simulation.getTime()
            else:
                pass
        else:
            print("WARNING UNKNOWN STATE", self.current_state)
        if self.intersection_name==DEBUG_CONTROLLER_LOG:
            print(self.current_state, self.timer, "State:", self.current_phase, self.pressures, traci.simulation.getTime()-self.current_gt_start)
            print("")
        self.setSignalOnTrafficLights()
            
    def determinePressures(self):
        if df_current_status is None:
            self.pressures = [0 for p in self.links]
            return
        self.pressures = []
        for link in self.links:
            lanes = self.links[link]
            df_vehicles = []
            # based on lane
            if type(df_vehicles)==list:
                df_vehicles = df_current_status[df_current_status["lane"].isin(lanes)]
            else:
                df_vehicles = pd.concat((df_vehicles, df_current_status[df_current_status["lane"].isin(lanes)]))
            # based on hidden on intersection
            edges = [l.split("_")[0] for l in lanes]
            hits = df_hidden_vehicles[df_hidden_vehicles["edge"].isin(edges)]
            if len(hits)>0:
                if type(df_vehicles)==list:
                    df_vehicles = df_hidden_vehicles[df_hidden_vehicles["edge"].isin(edges)]
                else:
                    df_vehicles = pd.concat((df_vehicles, df_hidden_vehicles[df_hidden_vehicles["edge"].isin(edges)][["veh_id", "lane", "class", "weight"]]))
            pressure = 0 
            if len(df_vehicles)>0:
                pressure = sum(df_vehicles["weight"])
            # multiplier
            if self.multiplier is not None:
                if link in self.multiplier:
                    pressure *= self.multiplier[link]
            self.pressures.append(pressure)
    
    def setSignalOnTrafficLights(self):
        traci.trafficlight.setPhase(self.intersection_name, self.current_phase)
        
controller1 = SignalController(
    intersection_name = "intersection1",
    phases = [0, 2, 4],
    links = {0:["921020465#1_3", "921020465#1_2", "921020465#1_2", "921020464#0_1", "921020464#1_1", "38361907_3", "38361907_2", "-1164287131#1_3", "-1164287131#1_2"], 
             2:["-1169441386_2", "-1169441386_1", "-331752492#1_2", "-331752492#1_1", "-331752492#0_1", "-331752492#0_2"], 
             4:["-183419042#1_1", "26249185#30_1", "26249185#30_2", "26249185#1_1", "26249185#1_2"]},
    )

controller2 = SignalController(
    intersection_name = "intersection2",
    phases = [0, 2, 4],
    links = {0:["183049933#0_1", "-38361908#1_1"], 
             2:["-38361908#1_1", "-38361908#1_2"], 
             4:["-25973410#1_1", "758088375#0_1", "758088375#0_2"]}
    )

controller3 = SignalController(
    intersection_name = "intersection3",
    phases = [0, 2, 4],
    links = {0:["E3_1", "-758088377#1_1", "-758088377#1_2", "-E1_1", "-E1_2"], 
             2:["E3_1", "E3_2"], 
             4:["-758088377#1_1", "-E1_1", "-E4_1", "-E4_2"]}
    )

controller4 = SignalController(
    intersection_name = "intersection4",
    phases = [0, 2],
    links = {0:["22889927#0_1", "758088377#2_1", "-22889927#2_1"], 
             2:["-25576697#0_1"]}
    )

controller5 = SignalController(
    intersection_name = "intersection5",
    phases = [0, 2, 4],
    links = {0:["E6_1", "E6_2", "E5_1", "130569446_1", "E15_1", "E15_2"], 
             2:["E15_2", "E6_3", "E5_2", "130569446_2"],
             4:["E10_1", "E9_1",  "1162834479#1_1", "-208691154#0_1", "-208691154#1_1"]},
    # multiplier={2:5}
    )
signal_controllers = [controller1, controller2, controller3, controller4, controller5]




# #############################################################################
# ## MAIN CODE
# #############################################################################

# LAUNCH SUMO
sumoConfigFile = "../model/Configuration.sumocfg" 
sumoCmd = [sumoBinary, "-c", sumoConfigFile, "--start", "--quit-on-end", "--time-to-teleport", "-1"]
traci.start(sumoCmd)

# LOAD VEHICLE SPAWN DATA
df_veh_spawn = pd.read_csv("../model/Spawn_Vehicles.csv")
df_veh_spawn = df_veh_spawn.rename(columns={"Unnamed: 0": "veh_ctr"})
df_bus_spawn = pd.read_csv("../model/Spawn_Bus.csv")
df_bus_spawn = df_bus_spawn.rename(columns={"Unnamed: 0": "veh_ctr"})

# LOAD EMISSION MODEL
emission_model = loadEmissionClassesFromFile(file="../data/Emission_VehiclePopulation.xlsx")

# INITIALIZE CONTROLLERS
if not CONTROL_MODE=="FIXED_CYCLED":
    for controller in signal_controllers:
        controller.current_gt_start = traci.simulation.getTime()

# RECORDER
veh_routes = {}
veh_classes = {}




# RUN SIMULATION
veh_ctr = 0
im_ctr = 0
selected_bus = None
selected_car = None
tracked = False
for current_time in simulation_times:#[161:]:
    # MEASURE
    df_current_status, df_hidden_vehicles = determine_current_state()
    if not CONTROL_MODE=="FIXED_CYCLED":
        # CONTROL / SET TRAFFIC LIGHTS
        for controller in signal_controllers:
            controller.doSignalLogic()
    # SPAWN CARS
    for idx, row in df_veh_spawn[df_veh_spawn["Adjusted_Datetime"]==current_time].iterrows():
        for x in range(0, int(np.ceil(row["n_spawn"]))):
            veh_ctr += 1
            spawnRandomVehicle(veh_ctr, desired_route=str(row["route"]))
            if im_ctr>1000 and selected_car is None and str(row["route"])=="route_E1_A18":
                selected_car = "VEH_"+str(veh_ctr)
                print(selected_car)
    # if selected_car is not None:
    #     break
    # SPAWN BUSSES
    for idx, row in df_bus_spawn[df_bus_spawn["Adjusted_Datetime"]==current_time].iterrows():
        veh_ctr += 1
        spawnRandomBus(veh_ctr, desired_route=str(row["route"]), stops=str(row["Stops"]))
        if im_ctr>0 and selected_bus is None and str(row["route"])=="route_R106":
            selected_bus = "BUS_"+str(veh_ctr)+"-"+str(row["route"])
            print(selected_bus)
    # RUN SIMULATION FOR ONE SECOND
    for n in range(0,SIMULATION_STEPS_PER_SECOND):
        im_ctr+=1
        traci.simulationStep()
        if selected_car is not None:
            # >> int a
            # traci.gui.setOffset("View #0", 1300, 1218)
            # traci.gui.setZoom('View #0', 1000)
            # >> int B
            # traci.gui.setOffset("View #0", 2034, 1680)
            # traci.gui.setZoom('View #0', 1000)
            # >> int C
            # traci.gui.setOffset("View #0", 1399, 1280)
            # traci.gui.setZoom('View #0', 1000)
            # >> top view
            # traci.gui.setAngle('View #0', -30)
            # traci.gui.setOffset("View #0", 1653, 1477)
            # traci.gui.setZoom('View #0', 200)
            # >> bus view
            # traci.gui.trackVehicle("View #0", selected_bus)
            # traci.gui.setZoom('View #0', 1500)
            # >> car view
            traci.gui.setZoom('View #0', 1500)
            traci.gui.trackVehicle("View #0", selected_car)
            
            traci.gui.screenshot('View #0', "figures/foto_"+"{0:0=3d}".format(im_ctr)+"Test.png")
    if DEBUG_GUI:
        time.sleep(SIMULATION_WAIT_TIME)
    if DEBUG_TIME:
        print(current_time)

# CLOSE SUMO
# traci.close()
