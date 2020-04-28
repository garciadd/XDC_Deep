"""
XDC_sat notebook utils 

Author: Daniel Garcia Diaz
Date: August 2018
"""
#APIs
import os, re
import glob
import requests
import argparse
import json
from osgeo import gdal, osr
import datetime
import matplotlib.pyplot as plt
import numpy as np
import subprocess
from zipfile import ZipFile

from urllib.parse import urlencode
from urllib.parse import quote, quote_plus

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
    onedata_path = '/mnt/onedata/XDC_LifeWatch'
    if not (os.path.isdir(onedata_path)):
        print ('Mounting ondedata space {}'.format('XDC_Lifewatch'))
        subprocess.Popen('/srv/job.sh', stdin=subprocess.PIPE)
     
    return onedata_path

def load_tiff_file(tif_path):
    
    src_ds = gdal.Open(tif_path)
    sr_bands = {}
    for band in range(src_ds.RasterCount):
        band += 1
        srcband = src_ds.GetRasterBand(band)
        
        if srcband is None:
            continue

        name = srcband.GetDescription()
        arr = srcband.ReadAsArray()
        sr_bands[name] = arr
        
    return sr_bands

def load_s2_file(zip_path):
    
    tile_path = os.path.splitext(zip_path)[0] + '.SAFE'
    if not (os.path.isdir(tile_path)):
        with ZipFile(zip_path, 'r') as zipObj:
            # Extract all the contents of zip file in different directory
            zipObj.extractall(region_path)
        
    # Process input tile name
    r = re.compile("^MTD_(.*?)xml$")
    matches = list(filter(r.match, os.listdir(tile_path)))
    if matches:
        xml_path = os.path.join(tile_path, matches[0])
    else:
        raise ValueError('No .xml file found.')

    bands = {10: ['B4', 'B3', 'B2', 'B8'],
             20: ['B5', 'B6', 'B7', 'B8A', 'B11', 'B12'],
             60: ['B1', 'B9', 'B10']}
        
    raster = gdal.Open(xml_path)
    datasets = raster.GetSubDatasets()

    for dsname, dsdesc in datasets:
        
        arr_bands = {}
        for res in bands.keys():
            if '{}m resolution'.format(res) in dsdesc:
                
                print('Loading bands of Resolution {}'.format(res))

                ds_bands = gdal.Open(dsname)
                data_bands = ds_bands.ReadAsArray()
                
                for i, band in enumerate(bands[res]):
                    arr_bands[band] = data_bands[i] / 10000
    
    return arr_bands

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
    global output_path

    local_path = mount_onedata()
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

def preprocessbutton_clicked(preprocessbutton):
    
    region = region_path.split('/')[-1]
    
    #load the downloaded files
    with open('regions.json') as file:
        regions = json.load(file)
    
    coord = regions[region]["coordinates"]
    coord = '[{},{},{},{}]'.format(coord['W'], coord['S'], coord['E'], coord['N'])
        
    # Deployment Orchestrator (temporal)
    api_url = 'http://193.146.75.183:10031/v2/models/satsr/predict/'
    
    for file in zip_file.value:
        
        print ('Preprocessing {} ...'.format(file))
        
        path = os.path.join(region_path, file)
        outpath = os.path.splitext(path)[0] + '.tiff'

        query = {'accept': 'image/tiff',
                 'satellite': '"sentinel2"',
                 'roi_x_y_test': 'null',
                 'roi_lon_lat_test': coord,
                 'max_res_test': 'null',
                 'copy_original_bands': 'true',
                 'output_file_format': '"GTiff"',
                 'output_path': 'null'}

        url = api_url + '?' + urlencode(query).replace('+', '%20')

        r = subprocess.run('curl -X POST "{}" -H "accept: image/tiff" -H "Content-Type: multipart/form-data" -F "data=@{};type=application/zip"'.format(url, path), shell=True, check=True, stdout=subprocess.PIPE).stdout

        with open(outpath, 'wb') as f:
            f.write(r)

def region_on_change(v):
    global region_path, zip_file
    
    clear_output()
    
    local_path = mount_onedata()
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
    
    preprocessbutton = widgets.Button(description='preprocess')
    
    tif_files = [os.path.basename(x) for x in glob.glob("{}/*.tiff".format(region_path))]
    nc_file = widgets.Select(options=preprocessed_files,
                             value=None,
                             description='raw_files',
                             disabled=False,
                             layout=Layout(width='90%'))
    
    hbox = HBox(children=[zip_file, preprocessbutton])
    preprocessing = VBox(children=[region, hbox, nc_file])
    user_interface.children = [ingestion, preprocessing, visualization]
    display(user_interface)
    
    preprocessbutton.on_click(preprocessbutton_clicked)
    
    
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
    

def file_on_change(v):
    
    tif_path = os.path.join(region_path, v['new'])
    sr_bands = load_tiff_file(tif_path)
    print (sr_bands)
    
    zip_path = os.path.splitext(tif_path)[0] + '.zip'
    arr_bands = load_s2_file(zip_path)
    print (arr_bands)

    
def region_on_change(v):
    global region_path
    
    clear_output()
    
    local_path = mount_onedata()
    region_path = os.path.join(local_path, v['new'])
    
    tif_files = [os.path.basename(x) for x in glob.glob("{}/*.tiff".format(region_path))]
    files = widgets.Dropdown(options=[tif_files[n] for n in range(len(tif_files))],
                             value=None,
                             description='files',)
    
    files.observe(file_on_change, names='value')
    
    visualization = VBox(children=[region, files])
    user_interface.children = [ingestion, preprocessing, visualization]
    display(user_interface)

def data_visualization(regions):
    global region
    
    region = widgets.Dropdown(options=[regions[n] for n in range(len(regions))],
                              value = None,
                              description='Available Regions:',)
    
    region.observe(region_on_change, names='value')
    
    visualization = VBox(children=[region])    
    return visualization

visualization = data_visualization(regions)


#Menu
user_interface = widgets.Tab()
user_interface.children = [ingestion, preprocessing, visualization]
user_interface.set_title(0,'Data Ingestion')
user_interface.set_title(1,'Preprocessing')
user_interface.set_title(2, 'Data Visualization')
user_interface
