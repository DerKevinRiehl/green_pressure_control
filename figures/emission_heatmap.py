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
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.colors as colors
import matplotlib.image as mpimg  # For loading images
from PIL import Image




# #############################################################################
# ## PARAMETERS
# #############################################################################
grid_resolution = 4.0  # m
heatmap_frame_border = 2
alpha = 55+180  # Rotation angle in degrees




# #############################################################################
# ## METHODS FOR LOADING
# #############################################################################
def loadTimeStepLogs(file):
    file_reader = open(file, "r")
    file_content = file_reader.read()
    file_reader.close()
    parts = file_content.split("<timestep time=\"")[1:]
    return parts

def extractInformationFromParts(parts):
    emission_info = []
    for part in parts:
        time = float(part.split("\"")[0])
        vehicle_parts = part.split("<vehicle id=")[1:]
        for vehicle_part in vehicle_parts:
            veh_pos_x = float(vehicle_part.split(" x=\"")[1].split("\"")[0])
            veh_pos_y = float(vehicle_part.split(" y=\"")[1].split("\"")[0])
            veh_em_co2 = float(vehicle_part.split(" CO2=\"")[1].split("\"")[0])
            veh_em_co = float(vehicle_part.split(" CO=\"")[1].split("\"")[0])
            veh_em_hc = float(vehicle_part.split(" HC=\"")[1].split("\"")[0])
            veh_em_nox = float(vehicle_part.split(" NOx=\"")[1].split("\"")[0])
            veh_em_pmx = float(vehicle_part.split(" PMx=\"")[1].split("\"")[0])
            veh_em_noise = float(vehicle_part.split(" noise=\"")[1].split("\"")[0])
            veh_em_aqi =  (veh_em_co2*0.15 + veh_em_co*0.10 + veh_em_hc*0.15 + veh_em_nox *0.30 + veh_em_pmx*0.30)/1000
            emission_info.append([
                time,
                veh_pos_x,
                veh_pos_y,
                veh_em_co2,
                veh_em_co,
                veh_em_nox,
                veh_em_pmx,
                veh_em_noise,
                veh_em_aqi
            ])
    return emission_info

def addSpatialDiscretization(emission_info, grid_resolution, alpha):
    emission_info_modified = []
    for info in emission_info:
        veh_pos_x = info[1]
        veh_pos_y = info[2]
        rotated_x, rotated_y = rotate_position(veh_pos_x, veh_pos_y, alpha)
        discretized_x, discretized_y = discretize_position(rotated_x, rotated_y, grid_resolution)
        emission_info_modified.append([discretized_x, discretized_y, *info])
    return emission_info_modified

def rotate_position(x, y, alpha):
    rad_alpha = np.radians(alpha)
    rotated_x = x * np.cos(rad_alpha) - y * np.sin(rad_alpha)
    rotated_y = x * np.sin(rad_alpha) + y * np.cos(rad_alpha)
    return rotated_x, rotated_y

def discretize_position(x, y, grid_resolution):
    discretized_x = round(x / grid_resolution) * grid_resolution
    discretized_y = round(y / grid_resolution) * grid_resolution
    return discretized_x, discretized_y

def prepareHeatmap(file):
    content_parts = loadTimeStepLogs(file)
    emission_info = extractInformationFromParts(content_parts)
    emission_info = addSpatialDiscretization(emission_info, grid_resolution, alpha)
    emission_info = pd.DataFrame(emission_info, columns=["grid_x", "grid_y", "time", "pos_x", "pos_y", "em_co2", "em_co", "em_nox", "em_pmx", "em_noise", "em_aqi"])
    emission_info_agg = emission_info.groupby(["grid_x", "grid_y"]).sum()
    del emission_info_agg["pos_x"]
    del emission_info_agg["pos_y"]
    del emission_info_agg["time"]
    emission_info_agg.reset_index(inplace=True)
    minx = -72 # min(emission_info_agg["grid_x"])
    maxx = 764 # max(emission_info_agg["grid_x"])
    miny = -2852 # min(emission_info_agg["grid_y"])
    maxy = -1660 # max(emission_info_agg["grid_y"])
    new_row_top_left = pd.DataFrame([[minx - heatmap_frame_border, miny - heatmap_frame_border, 0, 0, 0, 0, 0, 0]], columns=emission_info_agg.columns)
    new_row_bot_righ = pd.DataFrame([[maxx + heatmap_frame_border, maxy + heatmap_frame_border, 0, 0, 0, 0, 0, 0]], columns=emission_info_agg.columns)
    emission_info_agg_border = pd.concat([emission_info_agg, new_row_top_left, new_row_bot_righ], ignore_index=True)
    heatmap_data = emission_info_agg_border.pivot(index='grid_x', columns='grid_y', values='em_aqi')
    heatmap_data.fillna(0, inplace=True)
    heatmap_data = np.asarray(heatmap_data)[:, ::-1][::]
    return heatmap_data




# #############################################################################
# ## MAIN CODE
# #############################################################################
    # Load Heatmap From File
heatmap_data_mx = prepareHeatmap("../logs/logs_max_pressure/Emissions.xml")
heatmap_data_gr = prepareHeatmap("../logs/logs_green_pressure/Emissions.xml")
difference = np.cbrt(heatmap_data_mx - heatmap_data_gr[:,:-5])

# Display Heatmap
plt.rc('font', family='sans-serif') 
plt.rc('font', serif='Arial') 
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 4))
    # First subplot
cmap = LinearSegmentedColormap.from_list("custom_cmap",  [(1, 1, 1), (0, 0, 1)] , N=100)
im1 = ax1.imshow(heatmap_data_mx, origin='lower', cmap=cmap, aspect='auto')
ax1.set_xlim(10, 270)
ax1.set_ylim(50, 100)
ax1.set_title("(d) AQI Emission Heatmap (Max-Pressure)", fontweight="bold", y=0.8)
ax1.set_xlabel("")
ax1.set_ylabel("")
ax1.set_xticks([])
ax1.set_yticks([])
cbar_ax1 = fig.add_axes([0.8, 0.925, 0.15, 0.02])
cbar1 = fig.colorbar(im1, cax=cbar_ax1, orientation='horizontal')
cbar1.set_label('AQI Emissions [g]               ')
for spine in ax1.spines.values():
    spine.set_visible(False)
    # Second subplot
cmap_diverging = colors.LinearSegmentedColormap.from_list("custom_diverging", ['red', 'white', 'green'], N=100)
im2 = ax2.imshow(difference, origin='lower', cmap=cmap_diverging, aspect='auto')
ax2.set_xlim(10, 270)
ax2.set_ylim(50, 100)
ax2.set_title("(e) AQI Emission Reduction (by Green-Pressure)", fontweight="bold", y=0.8)
ax2.set_xlabel("")
ax2.set_ylabel("")
ax2.set_xticks([])
ax2.set_yticks([])
vmin = min(difference.min(), -difference.max())
vmax = max(-difference.min(), difference.max())
im2.set_clim(vmin, vmax)
cbar_ax2 = fig.add_axes([0.8, 0.44, 0.15, 0.02])
cbar2 = fig.colorbar(im2, cax=cbar_ax2, orientation='horizontal')
cbar2.set_label('Reduction [%]                     ')
for spine in ax2.spines.values():
    spine.set_visible(False)
plt.tight_layout()
plt.show()