"""
XDC_sat notebook utils 

Author: Daniel Garcia Diaz
Date: August 2018
"""
#APIs
import os
import glob
import requests
import argparse
import json
from netCDF4 import Dataset
from osgeo import gdal, osr
import datetime
import matplotlib.pyplot as plt
import numpy as np
import subprocess

#Map
from ipyleaflet import Map, basemaps, basemap_to_tiles, DrawControl

#widget
import ipywidgets as widgets
from ipywidgets import HBox, VBox, Layout
from ipywidgets import AppLayout, Button, GridspecLayout
from IPython.display import display
from IPython.display import clear_output

#sat module
from sat_server import sat

def get_coordinates(coord):

    W = np.round(coord[0][0] - 360, 3)
    S = np.round(coord[0][-1], 3)
    E = np.round(coord[2][0] - 360, 3)
    N = np.round(coord[2][-1], 3)

    coordinates = {}
    coordinates['W'], coordinates['S'] = W, S
    coordinates['E'], coordinates['N'] = E, N

    return coordinates

def satellite_args(inidate, enddate, region, coord, cloud, output_path):
    
    s2_args= {"inidate":inidate,
                      "enddate":enddate,
                      "region":region,
                      "coordinates":coord,
                      "platform": 'Sentinel-2',
                      "producttype": 'S2MSI1C',
                      "cloud":cloud,
                      'output_path': output_path
                      }
    
    l8_args= {"inidate":inidate,
                      "enddate":enddate,
                      "region":region,
                      "coordinates":coord,
                      "producttype": 'LANDSAT_8_C1',
                      "cloud":cloud,
                      'output_path': output_path
                      }
    
    return s2_args, l8_args

def mount_onedata():
    #mount onedata
    subprocess.Popen('/srv/job.sh', stdin=subprocess.PIPE)

############################## MENU ##################################

######################################
#########  Data Ingestion  ###########
######################################

#Date picker to choose the initial date
ini_date = widgets.DatePicker(
    description='Initial Date',
    disabled=False)

#Date picker to choose the end date
end_date = widgets.DatePicker(
    description='End Date',
    disabled=False)

#To choose the satellite. Drop down to select one
satellite = widgets.Dropdown(
    options=['Sentinel2', 'Landsat8', 'All'],
    value='All',
    description='Satellite:',
    disabled=False)

#To choose the region. Slot to write the name
name = widgets.Text(
    value = None,
    description='Region:',
    disabled=False)

#Slider for the cloud coverage
cloud = widgets.IntSlider(
    description='Cloud Coverage',)

#Run
namebutton = widgets.Button(description='Run')
mapbutton = widgets.Button(description='Run')
out = widgets.Output()

#widget without map
box = HBox(children=[ini_date, end_date, satellite])
box2 = HBox(children=[name, cloud])
grid = GridspecLayout(3, 3)
grid[0, :], grid[1, :], grid[2,1] = box, box2, namebutton

ingestion = VBox(children=[grid, out])

#Map to select the coordinates
m = Map(center=(41.975381, 358.489681), basemap=basemaps.Esri.WorldStreetMap, zoom=5)
draw_control = DrawControl(rectangle = {"shapeOptions": {"fillColor": "#fca45d",
                                                        "color": "#fca45d",
                                                        "fillOpacity": 0.7}})

draw_control.clear_polygons()
m.add_control(draw_control)

#To group the widgets
tab = VBox(children=[ini_date, end_date, satellite, name, cloud, mapbutton])

#Create grid to fill it in with widgets
mapgrid = GridspecLayout(2, 2)
mapgrid[:, 0], mapgrid[:, 1] = m, tab

def regionbutton_clicked(namebutton):

    local_path = '/mnt/onedata/XDC_LifeWatch'
    output_path = os.path.join(local_path, name.value)
    
    #load the downloaded files
    with open('regions.json') as file:
        regions = json.load(file)

    if name.value in regions:

        coord = regions[name.value]["coordinates"]
        inidate = (ini_date.value).strftime('%Y-%m-%d')
        enddate = (end_date.value).strftime('%Y-%m-%d')
        
        s2_args, l8_args = satellite_args(inidate, enddate, name.value, coord, cloud.value, output_path)
        
        if satellite.value == 'Sentinel2':
            sat.download_data(s2_args)
        elif satellite.value == "Landsat8":
            sat.download_data(l8_args)
        elif satellite.value == 'All':
            sat.download_data(s2_args)
            sat.download_data(l8_args)
        
    else:

        ingestion = VBox(children=[mapgrid, out])
        user_interface.children = [ingestion, visualization]

namebutton.on_click(regionbutton_clicked)

def mapbutton_clicked(mapbutton):

    coord = get_coordinates(draw_control.last_draw['geometry']['coordinates'][0])
    inidate = (ini_date.value).strftime('%Y-%m-%d')
    enddate = (end_date.value).strftime('%Y-%m-%d')
    local_path = '/mnt/onedata/XDC_LifeWatch'
    output_path = os.path.join(local_path, region.value)
    
    s2_args, l8_args = satellite_args(inidate, enddate, name.value, coord, cloud.value, output_path)
        
    if satellite.value == 'Sentinel2':
        sat.download_data(s2_args)
    elif satellite.value == "Landsat8":
        sat.download_data(l8_args)
    elif satellite.value == 'All':
        sat.download_data(s2_args)
        sat.download_data(l8_args)

mapbutton.on_click(mapbutton_clicked)

######################################
#######  Preprocessing  #########
######################################

def region_on_change(v):
    
    clear_output()
    
    local_path = '/mnt/onedata/XDC_LifeWatch'
#    if not (os.path.isdir(local_path)):
#        mount_onedata()
    region_path = os.path.join(local_path, v['new'])
        
    s2_files = [os.path.basename(x) for x in glob.glob("{}/*.zip".format(region_path))]
    l8_files = [os.path.basename(x) for x in glob.glob("{}/*.gz".format(region_path))]
    zip_files = s2_files + l8_files
        
    zip_file = widgets.SelectMultiple(options=zip_files,
                             value=tuple(zip_files[:1]),
                             description='raw_files',
                             disabled=False,
                             layout=Layout(width='90%'),
                             rows=len(zip_files))
    
    preprocessed_files = [os.path.basename(x) for x in glob.glob("{}/*.nc".format(region_path))]
    
    nc_file = widgets.Select(options=preprocessed_files,
                             value=None,
                             description='raw_files',
                             disabled=False,
                             layout=Layout(width='90%'))
    
    preprocessing = VBox(children=[region, zip_file, nc_file])
    user_interface.children = [ingestion, preprocessing, visualization]
    display(user_interface)
    
    
#load available regions
with open('regions.json') as data_file:
    regions_file = json.load(data_file)

regions = list(regions_file.keys())

def preprocess_data(regions):
    global region

    region = widgets.Dropdown(options=[regions[n] for n in range(len(regions))],
                              value = None,
                              description='Available Regions:',)
    
    region.observe(region_on_change, names='value')
    
    preprocessing = VBox(children=[region])    
    return preprocessing

preprocessing = preprocess_data(regions)
    
######################################
#######  Data Visualization  #########
######################################
######################################## Utils ##########################################

path = '/mnt/onedata/XDC_LifeWatch'

paths = {'main_path': path}

##################################### Functions for display Monochromatic band #########################################

def plot_on_change(v):

    dataset= Dataset(paths['band_path'], 'r', format='NETCDF4_CLASSIC')
    data = dataset[v['new']][:]
    vmin, vmax, mean, std = np.amin(data), np.amax(data), np.mean(data), np.std(data)
    stats = "STATS; min = {}, Max = {}, mean = {}, std = {}".format(vmin, vmax, mean, std)
    
    plt.figure(figsize=(7,7))
    
    with out_plot:
        
        clear_output()
        
        # Plot the image
        plt.imshow(data, vmin=vmin, vmax=vmax, cmap='Greys')

        # Add a colorbar
        plt.colorbar(label='Brightness', extend='both', orientation='vertical', pad=0.05, fraction=0.05)

        # Title axis
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.tick_params(axis='both', which='both', bottom=False, top=False, right=False, left=False, labelbottom=False, labelleft=False)

        # Add a title
        plt.title('{}'.format(v['new']), fontweight='bold', fontsize=10, loc='left')
        plt.suptitle(stats, x=0.92, y=0.92, fontsize='large')
        
        # Show the image
        plt.show()        

        
def file_on_change(v):
    
    global out_plot
    clear_output()
    
    list_files = names = [os.path.basename(x) for x in glob.glob("{}/*.nc".format(paths['region_path']))]
    list_files.sort()
    
    file = widgets.Dropdown(options=[list_files[n] for n in range(len(list_files))],
                            value = v['new'],
                            description='files:',)
    
    file.observe(file_on_change, names='value')
    
    top_box = HBox([file])
        
    band_path = os.path.join(paths['region_path'], v['new'])    
    paths['band_path'] = band_path
    
    dataset= Dataset(paths['band_path'], 'r', format='NETCDF4_CLASSIC')
    variables = dataset.variables
    variables = list(variables.keys())
    
    var = []
    for e in variables:
        if e not in ('lat', 'lon', 'spatial_ref'):
            var.append(e)
    
    bands = widgets.ToggleButtons(options=[var[n] for n in range(len(var))],
                                  description='Bands:',
                                  value = None,
                                  button_style='',)
    
    bands.observe(plot_on_change, names='value')
    
    out_plot = widgets.Output()
    
    bottom_box = HBox([bands])
    vbox = VBox([region, top_box, bottom_box, out_plot])
    visualization.children = [vbox, RGB_image, animation]
    user_interface.children = [ingestion, preprocessing, visualization]
    display(user_interface)

    
def region_on_change(v):
    
    global date, folders
    clear_output()
    
    region_path = os.path.join(path, v['new'])
    paths['region_path'] = region_path
        
    list_files = names = [os.path.basename(x) for x in glob.glob("{}/*.nc".format(paths['region_path']))]
    list_files.sort()
    
    file = widgets.Dropdown(options=[list_files[n] for n in range(len(list_files))],
                            value = None,
                            description='files:',)
    
    file.observe(file_on_change, names='value')
    
    top_box = HBox([file])

    vbox = VBox([region, top_box])
    visualization.children = [vbox, RGB_image, animation]
    user_interface.children = [ingestion, preprocessing, visualization]
    display(user_interface)
    
#################################################################################
    
def Monochromatic_band(regions):
    
    global region
        
    #Drop down to choose the available region
    region = widgets.Dropdown(options=[regions[n] for n in range(len(regions))],
                              value = None,
                              description='Available Regions:',)

    region.observe(region_on_change, names='value')
    vbox = VBox([region]) 
    
    return vbox


def RGB(regions):
    
    global region
        
    #Inicialización de widgets del menu
    #widgets para escoger region
    region = widgets.Dropdown(options=[regions[n] for n in range(len(regions))],
                              value = None,
                              description='Available Regions:',)
    
    region.observe(region_on_change, names='value')
    vbox = VBox([region]) 
    
    return vbox


def clip(regions):
            
    #Inicialización de widgets del menu
    #widgets para escoger region
    region = widgets.Dropdown(options=[regions[n] for n in range(len(regions))],
                              value = None,
                              description='Available Regions:',)

    vbox = VBox([region]) 
    
    return vbox

#####################################################################################

def data_visualization():
    
    global visualization, Band, RGB_image, animation
    clear_output()
        
    #load available regions
    with open('regions.json') as data_file:
        regions_file = json.load(data_file)
    
    regions = list(regions_file.keys())
    
    Band = Monochromatic_band(regions)
    RGB_image = RGB(regions)
    animation = clip(regions)
    
    #Menu
    visualization = widgets.Tab()
    visualization.children = [Band, RGB_image, animation]
    visualization.set_title(0, 'Monochromatic Band')
    visualization.set_title(1, 'RGB image')
    visualization.set_title(2, 'Animations')
    
    return visualization


visualization = data_visualization()
    
#Menu
user_interface = widgets.Tab()
user_interface.children = [ingestion, preprocessing, visualization]
user_interface.set_title(0,'Data Ingestion')
user_interface.set_title(1,'Preprocessing')
user_interface.set_title(2, 'Data Visualization')
user_interface
