"""To do list and summary:

  if methanol, then don't need BOG!!!
  give a list showing all phyiscal properties that is required for each fuel type



  implement NH3 and CH3OH, make some constrains variable to incorporate user inpt of fuel type.

  GWP20 of NH3 and CH3OH
  For pipelines, we convert total weight to pressure at necessary stages, and convert it back to total weight of H2.
  We fix the # of storage tanks and tank volume. each stage after calculation
  to deliver the same amount of H2 as LH2 limitation (1.63e7 kg H2) at 500 bar (density = 45 kg/m3), we need 145 H2 tanks...

1. change name of "start location" on the map to the eaxct locatiion name, same for end location
2. also provide the port name 
3. make it into a website 


4. higher efficiency of liquification, compressor...
5. try different fuels, CO2 factor (CH3OH, but cost high..)

8. opimization (best case and worst case for both CO2 and cost)

9. improve ship fuel consumption model
10. try to get global electricity price

cost/ kg H2, CO2/ kg h2

Original file is located at
    https://colab.research.google.com/drive/1q0hKHZTaUITqH-e4NboYycueNME1nU53

# Summary:

With 70,000 m3 4 shipping tanks (total 280,000 m3 which is 19600 tonnes, equivalent to Dead Weight Tonnage)
in-land tranpsort: 10% energy be saved with BOG reused for refrig. 

Large tank ship Fuel consumption: 0.239-0.288 metric tons of fuel per mile (200,000m3 LNG carrier), source:
https://maritimepage.com/ship-fuel-consumption-per-mile-or-how-much-fuel-does-a-cargo-ship-use/
With ref [13] which is the volume we applied (280,000 m3), propulsion is 50 MW at speed 18 knots, which is 108 metric ton of HFO/day 
and is 0.225 metric tone of HFO/mile. So this is a reasonable range.

# Todo:




3. diesel price - keep API there and take avg.
5. marine shipping price API
- currently only operational cost. Convert captical cost to operational cost as well?


**Finished**
1. Marine API distance uses nautical miles and has been converted inside the API function
1.  #!!!!!!!!! use CO2e of diesel for inland transport!!!!
2. calculate reliq and reuse of BOG on maritime transport based on this
- plant capacity of liquification in range of 1-10,000 kg/h
- Boiloff recirculation value 0~1 (make it a user-define) may include cost (another if function, recirculation cost from BOG), include it to everywhere, maybe zero during loading or in-land transport, but keep a variable there.
- Added refrig to each loading and unloading stage, shaft power is really really low. However, based on ref [3] eqn 18 to calculate BOG, results are not reasonable (like 20% loss). So still use overall BOR to calculate BOG.  
- check BOR values from Lee et al. 2019 cited in ref [3]: 0.3%/day is already given, no reference where this value from and it is for in-land storage. Claude says 0.1~0.5 %/day and trypically 0.2 %/day.
calculate BOR based on fundemental equations
- OHTC: from ref [3] cited
: "Züttel, A., 2003. Material for hydrogen" it's 0.03, but no OHTC value was found in their citation. So check with Claude, it says typical values of OHTC: 0.05 to 0.5 W/(m²·K), a well-design one should have around 0.1 W/(m²·K). Our process: 0.05~0.3.

- T effect on BOR for each stage -- ok, using slope for extrapolation, check if 1/4 makes sense.
- electricity price -- ok
- Refrigeration cost for storage -- ok.
- make total function in sequence -- OK, loading and unloading number seems not right
- fitting curve (advanced)
- can I use BOR_trans for both marine and land transportation? modified, found value for in-land BOR.
- CSV file for all the data

parameter study:
- distance LA to Chicago, fix LA and gradually move away from Chicago, vis versa 
- recirculation
- Temperature (for the study)
- V flowrate for cryo pump
- ship tank volume (from less to 70,000 m3 per tank)

User input on what to do with BOG (1. flare gas, 2. converted back to electricity, 3. leak


    Reference:



1.   Does a Hydrogen Economy Make Sense? 2006
2.   Technical assessment of liquefied natural gas, ammonia and methanol for overseas energy transport based on energy and exergy analyses, 2020
3.   A comparative study on energy efficiency of the maritime supply chains for liquefied hydrogen, ammonia, methanol and natural gas, 2022
4.  https://www.engineeringtoolbox.com/fuels-higher-calorific-values-d_169.html
5.  https://shipandbunker.com/prices
6.  https://www.engineeringtoolbox.com/hydrogen-d_1419.html
7.  https://www.epa.gov/system/files/documents/2024-02/ghg-emission-factors-hub-2024.pdf
8. https://www.gov.uk/government/publications/atmospheric-implications-of-increased-hydrogen-use
9. Liquid Hydrogen: A Review on Liquefaction, Storage,
Transportation, and Safety, 2021 (https://doi.org/10.3390/en14185917)
10. Hydrogen supply chain and challenges in largescale LH2 storage and transportation, Int. J. Hydrog. Energy 46 (2021) 24149-24168
11. Environmental life cycle assessment (LCA) comparison of hydrogen delivery options within Europe
12. An Extensive Review of Liquid Hydrogen in Transportation with Focus on the Maritime Sector. J. Mar. Sci. Eng. (2022), 10, 1222.
13. hydrogen fuelled LH2 tanker ship design, Ships and Offshore Structures (2022), 17:7, 1555-1564
14. https://maritimepage.com/ship-fuel-consumption-per-mile-or-how-much-fuel-does-a-cargo-ship-use/
15. https://www.nrel.gov/docs/fy99osti/25106.pdf
16. https://corridoreis.anl.gov/documents/docs/technical/apt_61012_evs_tm_08_2.pdf
17. https://doi.org/10.1016/j.ijhydene.2023.05.208
    reference: Assessing the pressure losses during hydrogen transport in the current natural gas infrastructure using numerical modelling, 2023
18. NIST Reference Fluid Thermodynamic and Transport Properties Database (REFPROP): Version 8.0
19. compressor and density reference:  https://doi.org/10.3390/hydrogen5020017
20. polytropic efficiency: https://www.recip.org/wp-content/uploads/2023/01/2022-EFRC-WhitePaper-Hydrogen-Compression.pdf
21. https://www.cnqixinggroup.com/fuel-tank/fuel-tank-trailer/38m3-stainless-steel-semi-trailer-for-liquid.html
22. https://yqftech.en.made-in-china.com/product/kJgUlKwvAFWQ/China-3-Axle-40000-Liters-Methanol-Ethanol-Tank-Tanker-Semi-Trailer-Tri-Axle-40m3-Ethanol-Methyl-Alcohol-Tank-Truck-Semi-Trailer-with-Stainless-Steel.html
23. https://doi.org/10.3390/en16134898
24. https://kleinmanenergy.upenn.edu/research/publications/ammonias-role-in-a-net-zero-hydrogen-economy/#:~:text=The%20theoretical%20minimum%20for%20such%20a%20process,5.92%20MWh/t%2DNH3%20(33.5%20MWh/t%2DH2)%20(Smith%20et%20al.&text=However%2C%20current%20best%20available%20technologies%20have%20efficiencies,energy%20required%20for%20electrolysis%20(Giddey%20et%20al.
25. https://doi.org/10.1016/j.ijhydene.2012.11.097

ref not used:
1. https://www.sustainable-ships.org/stories/2022/sfc
"""
# %% # User Input
# User Input

while True:
    start = input('Where is the start location? (location with state or country name) =>')
    if start:
        break
    else:
        print('Please enter a valid location.')

while True:
    end = input('Where is the end location? (location with state or country name) =>')
    if end:
        break
    else:
        print('Please enter a valid location.')

while True:
    fuel_type = input('What is your fuel type? 1. Hydrogen 2. Ammonia 3. Methanol => ')
    try:
        fuel_type = int(fuel_type) - 1  # Hydrogen = 0, Ammonia = 1, Methanol = 2
        if fuel_type == 0:
            print('Hydrogen selected')
            break
        elif fuel_type == 1:
            print('Ammonia selected')
            break
        elif fuel_type == 2:
            print('Methanol selected')
            break
        else:
            print('Not available. Please select a valid fuel type option.')
    except ValueError:
        print('Please enter a number (1, 2, or 3).')

# fuel_state_1 = ''
# fuel_state_2 = ''
# fuel_state = ''
# while fuel_state_1 & fuel_state_2 not in ['1' and '2']:
#     fuel_state_1 = input('How will fuel be transported at start location? 1. Liquid with trucks 2. Gas with pipelines =>')
#     fuel_state_2 = input('How will fuel be transported at end location? 1. Liquid with trucks 2. Gas with pipelines =>')
#     if fuel_state_1 & fuel_state_2 == '1':
#         fuel_state = '0'
#         print('Hydrogen will be transported in liquid phase with trucks at both locations.')
#     elif fuel_state_1 == '1' & fuel_state_2 == '2':
#         fuel_state = '1'
#         print('Hydrogen will be transported in liquid phase with trucks at start location and pressurized in pipelines at end location.')
#     elif fuel_state_1 == '2' & fuel_state_2 == '1':
#         fuel_state = '2'
#         print('Hydrogen will be transported in pressurized pipelines at start location and in liquid phase with trucks at end location.')
#     elif fuel_state_1 == '2' & fuel_state_2 == '2':
#         fuel_state = '3'
#         print('Hydrogen will be transported in pressurized pipelines at both locations.')
#     else:
#         print('Not available. Please select a valid option.')


# target_pressure_site_B = ''
# if fuel_state == ['1', '3']:
#    target_pressure_site_B = input('What is the target pressure at the end location? (unit: bar) =>')
#    target_pressure_site_B = float(target_pressure_site_B) if target_pressure_site_B else 200.0
#    print(f'Target pressure at the end location is {target_pressure_site_B} bar.')
# else:
#    print('No target pressure is needed at the end location.')
    



recirculation_BOG = ''
while recirculation_BOG not in ['1', '2']:
    recirculation_BOG = input('What do you want to do with all boil-off gas (BOG)? 1. expel, 2. recirculation => ')

    if recirculation_BOG == '1':
        print('No further treatment will be applied on boiloff H2.')
    elif recirculation_BOG == '2':
        print('Please provide more details in 3 stages: 1) in-land transport with trucks, 2) storage, 3) maritime transportation:')
    else:
        print('Not available, please select a valid option.')

if recirculation_BOG == '2':
    BOG_recirculation_truck_apply = ''
    BOG_recirculation_truck = input('What is the recirculation percentage (of BOG in %) in in-land transport? default 80% => (provide value between 0 and 100) ')
    BOG_recirculation_truck = float(BOG_recirculation_truck) if BOG_recirculation_truck else 80.0
    print(f'{BOG_recirculation_truck}% of BOG loss will be captured and reused.')

    while BOG_recirculation_truck_apply not in ['1', '2']:
        BOG_recirculation_truck_apply = input('What will BOG be used during in-land transportation? 1) re-liquified; 2) used as another energy source => ')

        if BOG_recirculation_truck_apply == '1':
            print('Re-liquefication of BOG will be used during in-land transportation.')
        elif BOG_recirculation_truck_apply == '2':
            print('Another energy source will be used during in-land transportation.')
        else:
            print('Not available, please select a valid option.')

    BOG_recirculation_storage_apply = ''
    BOG_recirculation_storage = input('What is the recirculation percentage (of BOG in %) in storage? default 80% => (provide value between 0 and 100) ')
    BOG_recirculation_storage = float(BOG_recirculation_storage) if BOG_recirculation_storage else 80.0
    print(f'{BOG_recirculation_storage}% of BOG loss will be captured and reused.')

    while BOG_recirculation_storage_apply not in ['1', '2']:
        BOG_recirculation_storage_apply = input('What will BOG be used during storage? 1) re-liquified; 2) used as another energy source => ')

        if BOG_recirculation_storage_apply == '1':
            print('Re-liquefication of BOG will be used during storage.')
        elif BOG_recirculation_storage_apply == '2':
            print('Another energy source will be used during storage.')
        else:
            print('Not available, please select a valid option.')

    BOG_recirculation_mati_trans_apply = ''
    BOG_recirculation_mati_trans = input('What is the recirculation percentage (of BOG in %) in maritime transportation? default 80% => (provide value between 0 and 100) ')
    BOG_recirculation_mati_trans = float(BOG_recirculation_mati_trans) if BOG_recirculation_mati_trans else 80.0
    print(f'{BOG_recirculation_mati_trans}% of BOG loss will be captured and reused.')

    while BOG_recirculation_mati_trans_apply not in ['1', '2']:
        BOG_recirculation_mati_trans_apply = input('What will BOG be used during maritime transportation? 1) re-liquified; 2) used as another energy source => ')

        if BOG_recirculation_mati_trans_apply == '1':
            print('Re-liquefication of BOG will be used during maritime transportation.')
        elif BOG_recirculation_mati_trans_apply == '2':
            print('Another energy source will be used during maritime transportation.')
        else:
            print('Not available, please select a valid option.')

storage_time = input('How many days will liquid H2 be stored at each sea port? (unit: days) default: 3 =>')
storage_time = float(storage_time) if storage_time else 3.0
print(f'Storage will take up to {storage_time} days.')

LH2_plant_capacity = input('What is the Liquid H2 plant capacity? (unit: kg/hr) range: 1~10,000, default: 1,000 =>')
LH2_plant_capacity = float(LH2_plant_capacity) if LH2_plant_capacity else 1000.0
print(f'Plant capacity is {LH2_plant_capacity} kg/hr.')

ship_tank_volume = input('What is the tank volume on LH2 carrier ship? (unit: m3) range: 1250~70,000, default: 70,000 with 4 tanks =>')
ship_tank_volume = float(ship_tank_volume) if ship_tank_volume else 70000.0
print(f'Tank volume on LH2 carrier ship is {ship_tank_volume} m3.')

ship_tank_shape = input('What is the shape of the tanks on LH2 carrier ship? 1. Capsule 2. Spherical =>')
if ship_tank_shape == 1:
    print('Capsule shape for shipping tanks is selected.')
else:
    print('Spherical shape for shipping tanks is selected.')



print('Calculation started...')

if recirculation_BOG == '1':
    BOG_recirculation_truck_apply = BOG_recirculation_storage_apply = BOG_recirculation_mati_trans_apply = 0

user_define = [10000, fuel_type, int(recirculation_BOG), int(BOG_recirculation_truck_apply), int(BOG_recirculation_storage_apply), int(BOG_recirculation_mati_trans_apply)]
# search_string = 'port authority'
# print(user_define)

# [A,B,C,D,E,F]
# [weight,1,1,0,0,0]
# [weight,1,2,1,1,1]
# ...
# [weight,3,2,2,2,2]
# [weight, 0 or 1 or 2 or 3, 2, 1 or 2, 1 or 2, 1 or 2]

# 2nd represents recirculation or not, if == 1; then the rest are 0.
#                                      if == 2; then the rest are either 1 or 2.
# 3rd, 4th, 5th represent which application will be used at in-land, storage, and maritime transportation. if == 1, then use re-liquified, if == 2, then used as electricity.

# %% # Pre-defined parameters (only run when User input is not used.)
# # Pre-defined parameters
"""# summary

Carbon intensity function gives the same CO2e for location in the same state, but different between states. EIA API might possibly make it work but it only gives values for the US, not for international. So maybe another module for US-only use...

## Outline

A - Hydrogen Production Site.
B - Hydrogen Delivery Site.

What do we want to achieve through this:
1. Cost of transporting Hydrogen
2. CO2 emissions in hydrogen transport
3. Efficiency loss in hydrogen transport.


We want to design a framework that works for 1, 2, and 3 in one go.
The framework will basically include the entire process from A to B.
For eg.
1. Hydrogen is produced at A.
2. It is liquified at A.
3. Stored in Cryogenic Tanks at A.  
4. Loaded into trucks (how many trucks to have enough hydrogen for one ship).
5. Truck transportation from A. to nearest port to A.
6. Loading onto ISO Shipping Container.
7. Loading of Shipping containers onto ships.
8. Maritime Transport
9. Unloading of shipping container.
10. Transfer from shipping container to truck containers.
11. Truck transportation to B.
12. Storage at B.
"""
# fuel_type = '' # 1 for liquid at both locations, 1 for liquid at A gas at B, 2 for gas at A and liquid at B, 3 for gas at both locations
fuel_type = 1 # 0 for hydrogen, 1 for ammonia, 2 for methanol

target_pressure_site_B = 200 #bar at port A for example, not using now, only for pressurized pipelines
# H2_weight= 280000*70  #m3 * kg/m3 = kg
user_define = [10000,int(fuel_type),2,2,2,2]
# # recirculation = [recirculation_B]
start = 'University of Nevada, Las Vegas, NV'
end = 'University of Missouri-St. Louis, MO'
LH2_plant_capacity = 1000 #kg/hr
BOG_recirculation_truck = BOG_recirculation_storage = BOG_recirculation_mati_trans = 50
storage_time = 3  #days
ship_tank_volume = 70000  #m3, this is for Hydrogen
start_electricity_price = 0.032 #$/MJ #remember to uncomment this in route details func. when running
start_port_electricity_price = 0.032 #$/MJ
end_electricity_price = 0.036 #$/MJ  
end_port_electricity_price = 0.036 #$/MJ

ship_tank_shape = 2 #1 for Capsule, 2 for spherical

# %% # Built-in function
# Built-in function
"""# Pre-run"""

import subprocess
import sys
import math
import pandas as pd
import numpy as np
import searoute as sr  
# ref: https://medium.com/shipping-intel/maritime-professionals-top-5-python-libraries-4e1189ca4207
# & https://pypi.org/project/searoute/

from scipy.optimize import fsolve
from scipy.optimize import minimize
import contextlib
import io
import matplotlib.image as mpimg
import openai
from openai import OpenAI
#from google.colab import drive
#drive.mount('/content/drive')

api_key_google = "AIzaSyCIkea3aIJFZ7EPsjpYFQro9FotousvYBM"
api_key_searoutes = "Vq8uFIHBQH9ZH2ImAFWkV46G10ztp47w3jd9FcRT"
# api_key_EIA = "uVFtQjHVsBabqVnoZ3DeZBsSJSRGUEMpaZssbayw"  #primary key, run out of quota 09/2024
api_key_EIA = "42xmcdYPXJ96l1Q9Y2zh2ThvMyuIs3BEWg32y5y7"  #backup key
api_key_weather = "e7f21b5f82194f8983644935241908"
api_key_openAI = "sk-bsO0zNbfZky9HFmigvIKHQuI-uJWTnXD5NxEsqHtAuT3BlbkFJNIMsldotgfbkKquKKNknWCLuAxlA_i8w5rOMI8O7IA"


import requests
import json
import urllib
from urllib.parse import urlencode
from urllib.parse import quote


"""Get Latitude and Longitude from any address or postalcode"""

def extract_lat_long(address_or_postalcode, data_type = 'json'):
  endpoint = f'https://maps.googleapis.com/maps/api/geocode/{data_type}'
  params = {'address': address_or_postalcode, 'key': api_key_google}
  url_params = urlencode(params)
  url = f'{endpoint}?{url_params}'
  r = requests.get(url)
  if r.status_code not in range(200, 299):
    return {}
  latlng = {}
#  try:
  data = r.json()
  latlng = r.json()['results'][0]['geometry']['location']
  state_name = next((component['long_name'] for component in data['results'][0]['address_components'] if'administrative_area_level_1'in component['types']), None)
#  except:
#    pass
  return latlng.get("lat"), latlng.get("lng"), state_name

"""Get Latitude and Longitude for in-land routes"""

from urllib.parse import urlencode

def extract_route_coor(origin, destination, mode='driving', alternatives=False):
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    
    origin = f"{origin[0]},{origin[1]}"
    destination = f"{destination[0]},{destination[1]}"
    params = {
        'origin': origin,
        'destination': destination,
        'key': api_key_google,
        'mode': mode,
        'alternatives': str(alternatives).lower()
    }
    
    url_params = urlencode(params)
    url = f'{endpoint}?{url_params}'
    
    response = requests.get(url)
    
    if response.status_code not in range(200, 299):
        return []
    
    data = response.json()
    
    if data['status'] != 'OK':
        return []
    
    coordinates = []
    
    for route in data['routes']:
        route_coordinates = []
        for leg in route['legs']:
            for step in leg['steps']:
                start_location = step['start_location']
                end_location = step['end_location']
                
                route_coordinates.append((start_location['lat'], start_location['lng']))
                
                # If polyline data is available, decode it to get more detailed coordinates
                if 'polyline' in step:
                    detailed_points = decode_polyline(step['polyline']['points'])
                    route_coordinates.extend(detailed_points)
                
                route_coordinates.append((end_location['lat'], end_location['lng']))
        
        coordinates.append(route_coordinates)
    
    return coordinates

def decode_polyline(polyline_str):
    """
    Decodes a polyline string into a list of latitude-longitude tuples.
    """
    index, lat, lng = 0, 0, 0
    coordinates = []
    while index < len(polyline_str):
        lat_change, lng_change = 0, 0
        for _ in range(2):
            shift = 0
            result = 0
            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if not byte >= 0x20:
                    break
            if result & 1:
                change = ~(result >> 1)
            else:
                change = result >> 1
            if _ == 0:
                lat_change = change
            else:
                lng_change = change
        lat += lat_change
        lng += lng_change
        coordinates.append((lat / 100000.0, lng / 100000.0))
    return coordinates


"""Get elevation out of latitude and longtitude."""

def elevation_cal(lat, lng):
  endpoint = f'https://maps.googleapis.com/maps/api/elevation/json'
  location = f'{lat},{lng}'
  url_params = {
      'key': api_key_google,
      'locations': location
  }
  url = f'{endpoint}?{urlencode(url_params)}'
  r = requests.get(url)
  elevation = r.json()['results'][0]['elevation']
  return elevation

### Unit in meters.

# print(round(elevation_cal(33.702578, -119.149040),1),'m')
"""Get the nearest port from (lat, long) with openAI"""

def openai_get_nearest_port(port_coor):
  client = OpenAI(api_key=api_key_openAI)

  response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "Verify coordinates correspond to actual port locations within 100km focus on deep-water/deep-draft ports suitable for large vessels"},
            {"role": "user", "content": f"""Given coordinates {port_coor}, return the nearest deep-water or deep-draft port's information in JSON format:
            {{
                "nearest_port": "PORT_NAME_HERE",
                "latitude": LATITUDE,
                "longitude": LONGITUDE
            }}"""},
        ]
    )
  output = response.choices[0].message.content
    
  try:
        result = json.loads(output)
        lat = result.get("latitude")
        lng = result.get("longitude")
        port_name = result.get("nearest_port")
        
        # Check if any required fields are missing
        if None in (lat, lng, port_name):
            return None, None, "Missing required port information in response"
            
        return lat, lng, port_name
  except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return None, None, "Error parsing the response"


"""(old method) Get the nearest port from (lat, long)"""

def get_nearest_port(latitude, longitude, search_string):
  base_endpoint_place = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
  params = {
    'key': api_key_google,
    'input': search_string,
    'inputtype':'textquery',
    'language': 'en',
    'fields':'html_attributions,name,geometry'}

  locationbias = f'point:{latitude},{longitude}'
  use_circular = False
  if use_circular:
    radius = 100
    locationbias = f'circle:{radius},{latitude},{longitude}'
  params['locationbias'] = locationbias

  params_encoded = urlencode(params)
  place_endpoint = f'{base_endpoint_place}?{params_encoded}'

  r = requests.get(place_endpoint)
  Port_name = {}
  Port_name = r.json()['candidates'][0]['name']
  lat = r.json()['candidates'][0]['geometry']['location']['lat']
  lng = r.json()['candidates'][0]['geometry']['location']['lng']
  return Port_name, lat, lng

"""Get total distance and time duration betweeen two inland locations"""

def inland_routes_cal(start, end):
   data_type = 'json'
   endpoint = f'https://maps.googleapis.com/maps/api/distancematrix/{data_type}'
   params = {'origins': start, 'destinations': end, 'key': api_key_google}
   url_params = urlencode(params)
   url = f'{endpoint}?{url_params}'

   output = requests.get(url).json()

   for obj in output['rows']:
      for data in obj['elements']:
        distance = data['distance']['text']
        duration = data['duration']['text']
   return distance, duration

def straight_line_dis(lat1, lon1, lat2, lon2):
    # Calculate the straight-line distance between two points using the Haversine formula
    R = 6371  # Radius of the Earth in kilometers
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c #unit: km
    return distance

"""Get info of sea routes
very inaccurate, so not using, replaced with searoute function
1.   https://www.shippingintel.com/sdk
2.   https://medium.com/shipping-intel/ai-powered-vessel-routing-d1be16c4029c

[2] An AI-powered routing API is forwarded for consideration below. The API uses GPT to search for ports and coordinates from an IMO-sourced port list, and then uses the EUs MARNET* to unpack an optimal route. The former enables API parameters to contain spelling errors, alternate port names, or aliases, while the latter preserves a grounded-truth-source. This type of augmented effort is, in the authors opinion, representative of the future of AI within the maritime domain.

*: Marine Atlantic Regions Network (MARNET) facilitates greater collaboration and knowledge exchange between marine socio economists, policy officers as well as Local and Regional Authorities, throughout the Atlantic Area. Leader: Socio Economic Marine Research Unit at NUI Galway, Ireland
"""

# def distance_port_to_port(port1, port2):
#     url = 'https://www.shippingintel.com/api/calculate_distance'

#     # Example payload if the API takes coordinates directly
#     data = {
#             'port1': port1,
#             'port2': port2
#     }

#     # Send POST request to the API
#     response = requests.post(url, data=data)
#     response_json = response.json()
#     distance = float(response_json['distance'])*1.852 #convert from nautical miles to km
#     print(response_json)
#     return distance

# def route_port_to_port(port1, port2):
#     url = 'https://www.shippingintel.com/api/calculate_route'

#     # Example payload if the API takes coordinates directly
#     data = {
#             'port1': port1,
#             'port2': port2
#     }

#     # Send POST request to the API
#     response = requests.post(url, data=data)
#     response_json = response.json()
#     route = response_json['route']
#     return route

"""Bunker price API (not finish)"""

# import http.client

# conn = http.client.HTTPSConnection("api.collectapi.com")

# headers = {
#     'content-type': "application/json",
#     'authorization': "apikey your_token"
#     }

# conn.request("GET", "/gasPrice/stateUsaPrice?state=WA", headers=headers)

# res = conn.getresponse()
# data = res.read()

# print(data.decode("utf-8"))

"""Electricity and Diesel price API from U.S. Energy Information Administration"""

##price in unit =[$/kWh]##

state_ids = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL',
    'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA',
    'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI',
    'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT',
    'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND',
    'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
    'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN',
    'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

def electricity_price(state_name):
    state_id = state_ids.get(state_name)

    if not state_id:
        state_id = 'CA'
        print("==> Destination not in the US, electricity price will use data from 'California'.")

    url = "https://api.eia.gov/v2/electricity/retail-sales/data/"
    params = {
      'frequency': 'monthly',
      'data[0]': 'price',
      'facets[stateid][]': state_id,
      'sort[0][column]': 'period',
      'sort[0][direction]': 'desc',
      'offset': 0,
      'length': 1,
      'api_key': api_key_EIA  # Replace with your actual EIA API key
      }

    response = requests.get(url, params=params)

    data = response.json()
    if data['response']['data']:
        current_price = round(float(data['response']['data'][0]['price'])*0.01,3)
        return current_price
    else:
        # params_1 = {**params, 'facets[stateid][]': 'TX'}
        # response_1 = requests.get(url, params=params_1)
        # data_1 = response.json()
        # current_price_1 = round(float(data_1['response_1']['data'][0]['price'])/2*0.01,3)
        #print("No data available, use half California electricity price instead",current_price, '$/kWh')
        return none # type: ignore

# from datetime import datetime, timedelta

# def seven_days_ago_date():
#     today = datetime.now()
#     seven_days_ago = today - timedelta(days=7)
#     return seven_days_ago.strftime("%Y-%m-%d")

# date = seven_days_ago_date()

# def get_diesel_price(area_code, date):
#     url = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
#     params = {
#         "frequency": "weekly",
#         "data[0]": "value",
#         "start": date,
#         "offset": 0,
#         "length": 5000,
#         "area-code": area_code,
#         "api_key": api_key_EIA
#     }

#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status()  # Raise an exception for HTTP errors
#         data = response.json()

#         # Debugging: Print the response to check its structure
#         print("Response Data:", data)

#         # Extract diesel price from the response
#         diesel_price = next(
#             (item['value'] for item in data.get('response', {}).get('data', [])
#              if 'Diesel' in item.get('product-name', '')),
#             None
#         )

#         return diesel_price

#     except requests.RequestException as e:
#         print(f"Error occurred: {e}")
#         return None

# if __name__ == "__main__":
#     area_code = 'CA'  # Example state code
#     date = "2024-08-19"  # Example date
#     price = get_diesel_price(area_code, date)
#     print(f"Diesel Price: ${price}")

def local_temperature(lat, lon):
    location = f"{lat},{lon}"
    api_key = api_key_weather
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={location}" #1 million times request per month
    response = requests.get(url)
    data = response.json()

    if response.status_code == 200:
        temperature = data['current']['temp_c']  # Temperature in Celsius
        return temperature
    else:
        return f"Error: {data.get('error', {}).get('message', 'Unable to fetch temperature data')}"


#temperature = local_temperature(latitude, longitude)
#print(f"The current temperature at ({latitude}, {longitude}) is {temperature}°C")

"""Carbon intensity: This endpoint retrieves the last known carbon intensity (in gCO2eq/kWh) of electricity consumed in an area. It can either be queried by zone identifier or by geolocation.

Ref: https://static.electricitymaps.com/api/docs/index.html#recent-carbon-intensity-history
"""

def carbon_intensity(lat, lng):
    url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
    headers = {"auth-token": 'x4kCYteScgVLu'}
    params = {"lat": lat, "lon": lng}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    CO2e = float(data['carbonIntensity'])
    # print(data)
    if response.status_code == 200:
        return CO2e
    else:
        return {
            "error": f"Failed to retrieve data: {response.status_code} - {response.text}"
        }

# print(carbon_intensity(38.7038727, -90.305756))
# print(carbon_intensity(44.044044, -123.075736))

import re

def time_to_minutes(time_str):
    # Extract hours and minutes using regular expressions
    hours_match = re.search(r'(\d+)\s*h', time_str)
    minutes_match = re.search(r'(\d+)\s*min', time_str)

    # Convert hours to minutes, if found
    hours = int(hours_match.group(1)) * 60 if hours_match else 0
    # Convert minutes, if found
    minutes = int(minutes_match.group(1)) if minutes_match else 0

    # Total time in minutes
    return hours + minutes

# Reality check:
# check even local CO2 intensity, like LA and SF

# gCO2/kWh=lbCO2/MWh * 0.453592

# based on the data (table 6) from EPA.gov: https://www.epa.gov/system/files/documents/2024-02/ghg-emission-factors-hub-2024.pdf

# 06/2024 California electricity CO2 factor is 497.4 (lb CO2 / MWh) which is 225 gCO2/kWh. From the API, it gives 297 gCO2/kWh.

# 06/2024 Texas electricity CO2 factor is 771.1 (lb CO2 / MWh) which is 349.4
# gCO2/kWh. From the API, it gives 414 gCO2/kWh

# 2021 Taiwan electricity CO2 factor is 509 (gCO2/kWh). From the API, it gives 557 gCO2/kWh
# 2023 Germany electricity CO2 factor is 381 (gCO2/kWh). From the API, it gives 430 gCO2/kWh
# 2023 France electricity CO2 factor is 56 (gCO2/kWh). From the API, it gives 17 gCO2/kWh"""
# %% # Route details & PyMaps
# Route details & PyMaps


coor_start = extract_lat_long(start)
coor_end = extract_lat_long(end)
route = sr.searoute((coor_start[1], coor_start[0]), (coor_end[1], coor_end[0]), units="nm") # https://pypi.org/project/searoute/
searoute_coor = route.geometry['coordinates']
searoute_coor = [[lat, lon] for lon, lat in searoute_coor]
start_port_coor = searoute_coor[0]
end_port_coor = searoute_coor[-1]
# start_port = get_nearest_port(start_port_coor[0], start_port_coor[1], search_string)
# end_port = get_nearest_port(end_port_coor[0], end_port_coor[1], search_string)
start_port = openai_get_nearest_port(start_port_coor)
end_port = openai_get_nearest_port(end_port_coor)

straight_dis_start_A_to_port = straight_line_dis(coor_start[0], coor_start[1], start_port[0], start_port[1])
straight_dis_port_B_to_end = straight_line_dis(coor_end[0], coor_end[1], end_port[0], end_port[1])

start_local_temperature = local_temperature(coor_start[0], coor_start[1])
end_local_temperature = local_temperature(coor_end[0], coor_end[1])
port_to_port_dis = route.properties['length'] * 1.852
# use print(route.properties['units']) to check the unit, it is nautical mile
# searoute_coor_list = route_port_to_port(start_port[0],end_port[0])
CO2e_start = carbon_intensity(coor_start[0], coor_start[1]) #gCO2/kWh
CO2e_end = carbon_intensity(coor_end[0], coor_end[1])
# start_electricity_price = electricity_price(extract_lat_long(start)[2])/3.6 #$/MJ
# end_electricity_price = electricity_price(extract_lat_long(end)[2])/3.6 #$/MJ


start_to_port = inland_routes_cal(start, start_port[2])
port_to_end = inland_routes_cal(end_port[2],end)
#sometimes if pass the port name (end_port[0]) directly to inland_routes_cal function, it would cause error out of no reason. So replace it with coordinates.


start_to_port_dis = start_to_port[0].split()[0].replace(',', '')
port_to_end_dis = port_to_end[0].split()[0].replace(',', '')
distance_A_to_port = float(start_to_port_dis)           #km
distance_port_to_B = float(port_to_end_dis)             #km
duration_A_to_port = time_to_minutes(start_to_port[1])  #min
duration_port_to_B = time_to_minutes(port_to_end[1])    #min

avg_ship_speed = 16 
max_ship_speed = 21
# DeadWeight Tonnage (DWT): this not only includes the weight of cargo but should also take into account the sum of the weights of fuel, freshwater, provision, ballast water, crew, and passengers
# The largest LNG tanker in the world: 
# IMO 9388819 (DWT: 155,159	 tonnes, avg/max 16/21), IMO 9388821 (DWT: 154,900 tonnes, avg/max 16/20.5)
# The most common tanker (in US):
# IMO 9763851 (DWT: 49,828 tonnes, avg/max 12/18), IMO 9693020 (DWT: 49,729 tonnes, avg/max 12/15), IMO 9704790 (DWT: 49,828 tonnes avg/max 12/15.5)
# use vesselfinder.com
port_to_port_duration = float(port_to_port_dis)/(avg_ship_speed*1.852)

"""Results"""

print(f"local temperature at {start}: {start_local_temperature}",'°C')
print(f'electricity price at {start}:',round(electricity_price(extract_lat_long(start)[2])/3.6,3), '$/MJ')
print('From',start,'to',start_port[2],':')
print(start_to_port[0],',',start_to_port[1])
print('')

print(f"Distance bewtween {start_port[2]} and {end_port[2]}: {round(port_to_port_dis,2)}",'km')
# print(f"Duration: {round(port_to_port_duration ,2)}",'hr', "based on avg speed")
# print(f"Avg Speed: 31.5",'km/h (17 knots)')

print('')
print(f"local temperature at {end}: {end_local_temperature}",'°C')
print(f'electricity price at {end}:',round(electricity_price(extract_lat_long(end)[2])/3.6,3), '$/MJ')
print('From',end_port[2],'to',end,':')
print(port_to_end[0],',',port_to_end[1])

####################################################################################
# Python maps

import folium


# centered around the midpoint of the two locations
midpoint = [(coor_start[0] + start_port[0]) / 2, (coor_start[1] + start_port[1]) / 2]
m = folium.Map(location=midpoint, zoom_start=4)

# Add markers for the locations
folium.Marker(coor_start[0:2], tooltip="start location").add_to(m)
folium.Marker(coor_end[0:2], tooltip="end location").add_to(m)

# Add road route (example coordinates, replace with actual route)
route_coor_start = extract_route_coor(coor_start[:2], start_port[:2])
route_coor_end = extract_route_coor(end_port[:2], coor_end[:2])
# road_route_start = [coor_start[0:2],start_port[1:]]
# road_route_end = [end_port[1:],coor_end[0:2]]
folium.PolyLine(route_coor_start, color="blue", weight=2.5, opacity=1).add_to(m)
folium.PolyLine(route_coor_end, color="blue", weight=2.5, opacity=1).add_to(m)

folium.PolyLine(searoute_coor, color="green", weight=2.5, opacity=1).add_to(m)

# m.save("map.html")
# Display the map
display(m)
# %% # Parameters
# Parameters

# ship_tank_radius = np.cbrt(ship_tank_volume/(10*np.pi))
# storage_area = 2*np.pi*(ship_tank_radius*ship_tank_height)  #m2, assuming the tank is a cylinder
if ship_tank_shape == 1:  #Capsule
    ship_tank_radius = np.cbrt(ship_tank_volume/(34/3*np.pi))
    ship_tank_height = 10*ship_tank_radius
    storage_area = 2*np.pi*(ship_tank_radius*ship_tank_height) + 4*np.pi*ship_tank_radius**2
else: #Spherical
    ship_tank_radius = np.cbrt(ship_tank_volume/(4/3*np.pi))
    storage_area = 4*np.pi*ship_tank_radius**2

HHV_chem = [142, 22.5, 22.7] #MJ/kg, ref [4] for H2
LHV_chem = [120, 18.6, 19.9] #MJ/kg, ref [4] for H2
boiling_point_chem = [20, 239.66, 337.7] #K
latent_H_chem = [449.6/1000, 1.37, 1.1] #MJ/kg, ref [3] for H2, boiling point -253. -33 and 64.7 C
specific_heat_chem = [14.3/1000, 4.7/1000, 2.5/1000]  #MJ/(kg K) = kJ/(kg K)* MJ/kJ,at 300 K, ref [3] for H2
chem_h_vaporization = [448.4, 1371.6, 1199] #kJ/kg, ref [6] for H2
HHV_heavy_fuel = 40 #MJ/kg, NEED ref!!!!!!
HHV_diesel = 45.6 #MJ/kg, ref [4]
liquid_chem_density = [71, 682, 805] #kg/m3, ref [2], -33C for ammonia (ref [23])
gas_chem_density = [0.09, 0.771, 1.33] #kg/m3, ref [4] for H2
heavy_fuel_density = 3.6 #kg/gal, ChatGPT
heavy_fuel_eff = 0.5 #ChatGPT
diesel_density = 3.22  #kg/gal, ref [4] A gallon of diesel fuel typically weighs around 7.1 pounds (3.22 kg)
diesel_price = 4.5 #$/gal, need API!
diesel_engine_eff = 0.4
electricity_price = 0.1/3.6 #$/MJ = $/kWh*1 kWh/3.6 MJ, need API!
marine_shipping_price = 610 #$/metric ton, ref [5], need API!
CO2e_diesel = 10.21  #kgCO2/gal, ref [7] table 2: emission factor of diesel
CO2e_heavy_fuel = 11.27  #kgCO2/gal, ref [7] table 2: emission factor of GH gas "residual fuel oil"
GWP_chem = [33,0,0]  #!!! fator, between 20 and 44 based on GWP20, GWP100 = 11, ref [8] section 6.4
fuel_cell_eff = 0.65  #typical fuel cell efficiency: 65%
road_delivery_ener = [0.0455/500, 0.022/500, 0.022/500] #ref[1] fig. 6, Energy needed for the road delivery: 5%/500 km for LH2, only hydrogen and methanol, assume NH3 same as methanol

BOR_land_storage = [0.0032, 0.0001, 0.0000032] #%/day, ref [3] table 7, from Fig 3 get equation , ammonia and methanol from ref [2]
BOR_loading = [0.0086, 0.00022, 0.0001667]  #%/day, ref [3] table 7
BOR_truck_trans = [0.005, 0.00024, 0.000005]   #%/day, Claude: A typical LH2 BOR in well-designed, modern cryogenic tanker trucks is approximately 0.5% per day
BOR_ship_trans = [0.00326, 0.00024, 0.000005]  #%/day, ref [3] table 7, ammonia and methanol from ref [2]
BOR_unloading = [0.0086, 0.00022, 0.0001667]  #%/day, ref [3] table 7
#####

energy_conversion_to_chem = [0, 43, 10.2/3600*1000/0.7]  #MWh/t-H2
#ref 24, NH3 obtained from H2 from SMR, if from electrolysis, it's 56.768 MWh/t-H2 realistically
#ref 25, conversion from H2 to CH3OH is exothermic, leading to small heat required to produce methanol from H2 is 10.2 MJ/kg-H2. 70% CH3OH production efficiency from Wikipedia


#####
#Loading to truck check:
ss_therm_cond = 0.03 #W/(m K) ref [3] table 5
pipe_inner_D = 0.508 #m, ref [3] table 5
pipe_thick = 0.13 #m, ref [3] table 5
pipe_length = 1000 #m ref [3] table 5

engine_power = 15 #MW For chemical tankers traveling at an avg speed 17 knots, engine power is in the range of 10 to 15 MW.
propul_eff = 0.55 #ref [3] table 4
install_power = 31 #MW, ref [3] table 4
hotel_load = 6 #MW, ref [3] table 4

V_flowrate = [72000, 72000, 72000]  #!! kg/hr ref [12] p.10: cryo pump flow rate, desired ranges between 300 and 1200 kg/min * 60 min/hr (18000 ~ 72000 kg/hr, use as user define), assume to be the same for methanol and ammonia
head_pump = 110 #m, ref [3] eqn 11
pump_power_factor = 0.78 #ref[3] eqn 11

tank_metal_thickness = 0.01 #m, Claude: Inner wall: 5-10 mm stainless steel
tank_insulator_thickness = 0.4 #m, Claude: 30-50 cm of multilayer insulation and vacuum
tank_metal_density = 7900 #kg/m3, ref [3] table 2
tank_insulator_density = 100 #kg/m3, ref [3] table 2
metal_thermal_conduct = 13.8 #W/(m K), ref [3] table 2
insulator_thermal_conduct = 0.02 #W/(m K), ref [3] table 2

#LH2_plant_capacity = 1000 #kg/h, ref [1] fig 5: H2 liquefication plant capacity

chem_in_truck_weight = [4200, 32000, 40000*0.001*liquid_chem_density[2]] #kg,ref [1] p1832, ref [15] p.33: 360 ~ 4300 kg for H2, ref [21],[22] for ammonia and methanol (40000 liter) 
truck_weight = [40*1000, 32000/0.7, 40000*0.001*liquid_chem_density[2]/0.7] #kg, ref [1] p1831, typically 60~80% of total weight is loading weight
# H2_in_truck_weight = 2100 #kg,ref [1] p1832: a large truck has room for about 2100 kg of the cryogenic liquid
truck_tank_volume = 50 #m3, ref [9] chapter 4.2: range 45 - 60 m3
truck_tank_length = 12 #m, from ChatGPT, typically 12-15 m
truck_tank_radius = np.sqrt(truck_tank_volume/(np.pi*truck_tank_length)) #m
truck_tank_metal_thickness = 0.005 #m, Claude: Typically 3 mm to 6 mm
truck_tank_insulator_thickness = 0.075 #m, Calude: Total insulation thickness including vacuum space: 50 mm to 100 mm (vacuum 25-50 mm)
number_of_trucks = None

number_of_cryo_pump_load_truck_site_A = 10 #randomly chosen, it's different at each location!!!
number_of_cryo_pump_load_storage_port_A = 10
number_of_cryo_pump_load_ship_port_A = 10
number_of_cryo_pump_load_storage_port_B = 10
number_of_cryo_pump_load_truck_port_B = 10
number_of_cryo_pump_load_storage_site_B = 10
number_of_cryo_pump_load_site_B = 10
# storage_volume = user_define[0]*15/1000 #m3, based on AI, storage size depends on the amount of LH2: 1 tonne of LH2 requires 15 m3 storage.
                                        #Same scaling between 100 kg to 100 tonnes. storage volume (m3) = total_H2_weight *15/1000
                                        #user_define[0] will be re-defined based on the target weight after optimization process
                                        #However, based on ref [10] fig 5, the largest storage size is only 3200 ~ 3400 m3
storage_volume = [5683, 50000000/liquid_chem_density[1], 50000000/liquid_chem_density[2]] #m3, ref [12] p.9: NASA commissioned the construction of a larger stationary tank with a volume of 1.25 million gallons (approx. 5683 m3), ref [23] for Ammonia storage: 50,000 ton at 1 atm
storage_radius = [np.cbrt(3 * volume / (4 * np.pi)) for volume in storage_volume] #meter, checked!
stroage_heat_transfer_coeff = 0.3 #W/(m2 K), given by ChatGPT: For insluated in-land storage, U-values are generally lower, often ranging from 0.2 to 0.6 W/m²·K.
shipping_heat_transfer_coeff = 0.4 #W/(m2 K), given by ChatGPT: For insulated marine containers, the U-value typically ranges from 0.3 to 0.7 W/m²·K.
truck_heat_transfer_coeff = 0.5 #W/(m2 K), given by ChatGPT: For Insulated Trucks, U-values typically range from 0.3 to 0.6 W/m²·K
# ship_tank_volume = 10000 #m3, ref [10] P.24159: HySTRA JV launched the world's first LH2 carrier ship with a single LH2 storage tank with a capacity of 1250 m3
ship_number_of_tanks = 4 # ref [13]
# ship_tank_height = 138   #m, ref [13] table 4
# ship_tank_radius = 13.19 #m, ref [13] table 4
ship_tank_metal_thickness = 0.02 #m, ref [13] table 4
ship_tank_insulator_thickness = 0.434 #m, ref [13] table 4
ship_fuel_consumption = 0.23 #metric ton/mi. !!convert 50MW from ref [13], ref [14] gives range of 0.239-0.288 metric ton/mile (200,000m3 LNG carrier)
OHTC_ship = [0.05, 0.22, 0.02] #W/(m2 K) 0.03 from ref [3] table 1, 0.27 for in-land transport and 0.05 for in-land storage, use 0.05 here, ref [2] for ammonia and methanol
ship_engine_eff = 0.6

COP_reliq = [0.036, 1.636, 2] #coefficient of performance, ref 3 table 6
COP_liq = [0.131, 1.714, 2] #coefficient of performance, ref 3 table 6
COP_refrig = [0.131, 1.714, 2] #coefficient of performance for cool down, ref 3 table 6

dBOR_dT = [(0.02538-0.02283)/(45-15)/4, (0.000406-0.0006122)/(45-15)/4, 0]    #BOR/(day K), *1/4 meaning it's the sum of 4 processes, ref [3] table 7 and fig 3(left, blue curve)
#correlation of plant capacity to energy required for LH2 production, data fitting from ref [1] fig 5
def liquification_data_fitting(H2_plant_capacity):
  # include advanced curve, user input (stadard or advnaced)
  x = H2_plant_capacity
  y0, x0, A1, A2, A3, t1, t2, t3 = 37.76586, -11.05773, 6248.66187, 80.56526, 25.95391, 2.71336, 32.3875, 685.33284
  energy_required = y0 + A1*np.exp(-(x-x0)/t1) + A2*np.exp(-(x-x0)/t2) + A3*np.exp(-(x-x0)/t3)
  return energy_required

def PH2_transport_energy(distance): #ref [1] fig 7
   x = distance
   energy_required = 10**(-5)*x**2 - 0.0197*x + 149.83
   return energy_required

def colebrook(f, Re, epsilon, D):
    return 1 / math.sqrt(f) + 2 * math.log10((epsilon / D) / 3.7 + 2.51 / (Re * math.sqrt(f)))   
def solve_colebrook(Re, epsilon, D):
    # Initial guess for f (typical value is 0.02)
    initial_guess = 0.02
    # Use fsolve to solve for f
    friction_factor, = fsolve(colebrook, initial_guess, args=(Re, epsilon, D))
    return friction_factor

def PH2_pressure_fnc(density):  #data from ref [19]
   x = density
   p = 0.2096*x**2 + 9.4904*x + 6.871
   return p #bar

def PH2_density_fnc(pressure):  #reverse fitting as previous function, from ref [19]
   x = pressure
   density = -3*10**(-5)*x**2 + 0.0769*x + 0.2059
   return density

def kinematic_viscosity_PH2(pressure):  #pressure unit: bar, ref [18]
  density = PH2_density_fnc(pressure) #kg/m3
  dynamic_vis = pressure*3.4255*10**(-9)+8.8366*10**(-6)  #Pa*s
  kine_vis = dynamic_vis/density
  return kine_vis #m2/s

def multistage_compress(pressure): #ref [19], use n = 1.36 as a isentropic process
   energy = 1.1751*pressure**0.401
   return energy #MJ/kg H2

EIM_liquefication = 100 #Efficiency improvement multiplier, from reference it will be 100%. Advanced technology reference and plotting:
EIM_cryo_pump = 100
EIM_truck_eff = 100
EIM_ship_eff = 100
EIM_refrig_eff = 100
EIM_fuel_cell = 100

img_LH2_current = mpimg.imread('LH2 current tech.jpeg')
img_LH2_plant_curve = mpimg.imread('H2 plant cap curve image.png')

pipeline_diameter = 48/39.37 #meter, NG typical size: 48 inches for transmission (larger than distribution), ref [16] page 3, ref [1] use 1 meter directly
epsilon = 0.04572*0.001 #m, roughness of steel, ref [17] page 34466, X52 steel roughness 
PH2_storage_V = 2500  #m3, chatgpt above-ground gaseous hydrogen storage tanks at Rotterdam with volume 2,500 m3 in pressure range 200 to 700 bar 
numbers_of_PH2_storage = 100
compressor_velocity = 31.3 #m/s, ref [1] p.1832, value based on Reynolds number, assume same velocity for all pressure range
multistage_eff = 80 #%, Typical polytropic efficiencies range from 70 to 90% (Gallick, 2006), ref [20] p.18
numbers_of_PH2_storage_at_start = 100


# reference: https://www.linkedin.com/posts/dawenger_hydrogen-hydrogen-missionhydrogen-activity-7242177179923496960-Pn1d/?utm_source=share&utm_medium=member_android
import matplotlib.pyplot as plt
# plt.imshow(img_LH2_current)
# plt.show()
# plt.imshow(img_LH2_plant_curve)
# plt.show()
##Capital cost (per year) + Operational cost
# %% # Process functions
# Process functions

def site_A_chem_production(A,B,C,D,E,F):  #The production process of H2 in gas-phase, probably by steam methane reforming or electrolysis.
  eff = 1
  #ener_consumed = A*HHV_H2/eff
  #money = NoCal_H2_price*A
  convert_energy_consumed = energy_conversion_to_chem[B]*1/1000*A*3600 #MWh/ton H2 * ton/kg * ton H2 * 3600 s/hr = MJ
  money = convert_energy_consumed*start_electricity_price
  G_emission = convert_energy_consumed*0.2778*CO2e_start*0.001  #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  BOG_loss = 0
  
  return money, convert_energy_consumed, G_emission, A, BOG_loss

def site_A_chem_liquification(A,B,C,D,E,F):  #The process that turns H2 from gas-phase to liquid-phase with energy resources from compression works. Due to
                                    #the complexity of this process, the energy consumed will be calculated based on curve extrapolation.
  if B == 0:  #LH2
    liquify_energy_required = liquification_data_fitting(LH2_plant_capacity)/(EIM_liquefication/100) #MJ/kg
  elif B == 1:  #Ammonia, commonly liquified at -33C or pressurized at 10 bar, here we choose liquification
    liquify_heat_required = specific_heat_chem[B]*(start_local_temperature+273-boiling_point_chem[B]) + latent_H_chem[B] #MJ/kg
    liquify_energy_required = liquify_heat_required/COP_liq[B] #MJ/kg, ref [3]
  else: #Methanol, liquid already
    liquify_energy_required = 0 #no heat liquification required for NH3

  liquify_ener_consumed = liquify_energy_required*A #MJ/kg*kg = MJ
  liquify_money = liquify_ener_consumed*start_electricity_price #MJ*$/MJ = $
  G_emission = liquify_ener_consumed*0.2778*CO2e_start*0.001 #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  BOG_loss = 0.016*A  #ed in Table 5. A hydrogen loss of 1.6 % was assumed during liquefaction in ref [11] page 21
  return liquify_money, liquify_ener_consumed, G_emission, A, BOG_loss

def chem_site_A_loading_to_truck(A,B,C,D,E,F):  #The liquified H2 (LH2) are loaded into tanks on trucks for in-land transport from the LH2 production site to the port.
  duration = A/(V_flowrate[B])/number_of_cryo_pump_load_ship_port_A #hr = kg/(kg/hr) 
  local_BOR_loading = dBOR_dT[B]*(start_local_temperature-25)+BOR_loading[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = local_BOR_loading*(1/24)*duration*A  #kg = %/day * day/hr *hr * kg
  pumping_power = liquid_chem_density[B]*V_flowrate[B]*(1/3600)*head_pump*9.8/(367*pump_power_factor)/(EIM_cryo_pump/100) #W: kg/m3 * m3/hr * hr/s * m * m/s^2 = kg/s*m2/s2 = W, ref [3] eqn 11
  q_pipe = 2*np.pi*ss_therm_cond*pipe_length*(start_local_temperature-(-253))/(2.3*np.log10((pipe_inner_D+2*pipe_thick)/pipe_inner_D))    #W, ref [3], equ 17 and table 5
  ener_consumed_refrig = (q_pipe/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*duration*3600  #MJ = J/s * MJ/J * hr * s/hr
  ener_consumed = pumping_power*duration*3600*1/1000000 + ener_consumed_refrig #J/s * hr * s/hr * MJ/J = MJ
  A -= BOG_loss
  money = ener_consumed*start_electricity_price #MJ*$/MJ = $
  #money from electricity
  G_emission = ener_consumed*0.2778*CO2e_start*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  return money, ener_consumed, G_emission, A, BOG_loss

def site_A_to_port_A(A,B,C,D,E,F):    #This process calculates the costs of the in-land route transporting with trucks between the production site and port.
  global number_of_trucks
  truck_energy_consumed = road_delivery_ener[B]*HHV_chem[B]  # %/km * MJ/kg = MJ/(kg km), ref [1] fig 6
  
  number_of_trucks = A/chem_in_truck_weight[B]
  # print('To deliver this amount of LH2,',round(number_of_trucks,0),'number of trucks is required for in-land transportation.')
  trans_energy_required = truck_energy_consumed*distance_A_to_port*A #MJ/(kg km)*#*km*kg = MJ
  diesel_money = trans_energy_required/HHV_diesel/diesel_density*diesel_price #MJ/(MJ/kg)/(kg/gal) * ($/gal)
  ### Refrig
  storage_area = 2*np.pi*truck_tank_radius*truck_tank_length  #m2, here storage size depends on the initial H2 weight (10,000 kg for example)
  if B == 0:
    thermal_resist = truck_tank_metal_thickness/metal_thermal_conduct + truck_tank_insulator_thickness/insulator_thermal_conduct #m/(W/(m K)) = (m2 K)/W, ref [3] eqn  6& 7
    OHTC = 1/thermal_resist #W/(m2 K), ref [3] eqn 5
  else:
    OHTC = OHTC_ship[B] #W/(m2 K), ref [3] table 1

  heat_required = OHTC*storage_area*(start_local_temperature+273-20) #W = W/(m2 K)* m2 * K, ref [3] eqn 16
  refrig_ener_consumed = (heat_required/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*60*duration_A_to_port*number_of_trucks #MJ = J/s * MJ/J * s/min   ref [3] eqn 1
  ###
  local_BOR_truck_trans = dBOR_dT[B]*(start_local_temperature-25)+BOR_truck_trans[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = A*local_BOR_truck_trans/(24*60)*duration_A_to_port #kg =  kg* %/day * day/hr * hr/min * min)

  refrig_money = (refrig_ener_consumed/(HHV_diesel*diesel_engine_eff*EIM_truck_eff/100))/diesel_density*diesel_price
  money = diesel_money + refrig_money #$ = $ + [MJ/(MJ/kg)]/(kg/gal) *$/gal
  total_energy = trans_energy_required + refrig_ener_consumed
  A -= BOG_loss
  G_emission_energy = (total_energy*CO2e_diesel)/(HHV_diesel*diesel_density) # (MJ* kgCO2/gal)/(MJ/kg * kg/gal) 
  G_emission = G_emission_energy + BOG_loss*GWP_chem[B] #kgCO2 = kgCO2 + kgH2 * kgCO2/kgH2

  ##recirculation
  if C == 2:
    ##1) reliq BOG
    if D == 1:
      usable_BOG = BOG_loss*BOG_recirculation_truck*0.01 #kg
      BOG_flowrate = usable_BOG/duration_A_to_port*60 #kg/hr = kg/min *min/hr
      reliq_ener_required = liquification_data_fitting(BOG_flowrate)/(EIM_liquefication/100)  #MJ/kg
      reliq_ener_consumed = reliq_ener_required*usable_BOG #MJ/kg*kg = MJ
      # reliq_ener_consumed_extra = (heat_required/COP_reliq)/1000000*60*duration_A_to_port*number_of_trucks
      total_energy = reliq_ener_consumed + trans_energy_required + refrig_ener_consumed #+ reliq_ener_consumed_extra
      reliq_money = (reliq_ener_consumed/(HHV_diesel*diesel_engine_eff*EIM_truck_eff/100))/diesel_density*diesel_price #$ = MJ/(MJ/kg)/(kg/gal) * ($/gal)
      money = diesel_money + reliq_money + refrig_money
      A += usable_BOG
      BOG_loss = BOG_loss*(1-BOG_recirculation_truck*0.01)
      G_emission_energy = total_energy/HHV_diesel/diesel_density*CO2e_diesel #MJ/(MJ/kg)/(kg/gal) * kgCO2/gal
      G_emission = G_emission_energy + BOG_loss*GWP_chem[B] #kgCO2 = kgCO2 + kgH2 * kgCO2/kgH2

    ##2) reuse BOG to produce electricity from fuel cells
    elif D == 2:
      usable_BOG = BOG_loss*BOG_recirculation_truck*0.01 #kg
      usable_ener = usable_BOG * fuel_cell_eff * EIM_fuel_cell/100 * LHV_chem[B] #MJ = kg * MJ/kg
      ener_consumed = refrig_ener_consumed - usable_ener
      refrig_money_save = (usable_ener/(HHV_diesel*diesel_engine_eff*EIM_truck_eff/100))/diesel_density*diesel_price
      money_save = refrig_money - refrig_money_save
      if ener_consumed < 0:
        ener_consumed = 0
        money = diesel_money
        total_energy = trans_energy_required
      else:
        money = diesel_money + money_save
        total_energy = trans_energy_required + ener_consumed
      BOG_loss = BOG_loss*(1-BOG_recirculation_truck*0.01)
      G_emission_energy = total_energy/HHV_diesel/diesel_density*CO2e_diesel #MJ/(MJ/kg)/(kg/gal) * kgCO2/gal
      G_emission = G_emission_energy + BOG_loss*GWP_chem[B] #kgCO2 = kgCO2 + kgH2 * kgCO2/kgH2
    else:
      False
  else:
    False
  return money, total_energy, G_emission, A, BOG_loss

def port_A_unloading_to_storage(A,B,C,D,E,F): #As trucks arrive at sea port, LH2 are unloaded for temporal storage, waiting to be cleared and
  duration = A/(V_flowrate[B])/number_of_cryo_pump_load_storage_port_A #hr = kg/(kg/m3 * m3/hr)
  local_BOR_unloading = dBOR_dT[B]*(start_local_temperature-25)+BOR_loading[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = local_BOR_unloading*(1/24)*duration*A #kg = %/day * day/hr *hr * kg
  pumping_power = liquid_chem_density[B]*V_flowrate[B]*(1/3600)*head_pump*9.8/(367*pump_power_factor) #W: kg/m3 * m3/hr * hr/s * m * m/s^2 = kg/s*m2/s2 = W, ref [3] eqn 11
  q_pipe = 2*np.pi*ss_therm_cond*pipe_length*(start_local_temperature-(-253))/(2.3*np.log10((pipe_inner_D+2*pipe_thick)/pipe_inner_D))    #W, ref [3], equ 17 and table 5
  ener_consumed_refrig = (q_pipe/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*duration*3600  #MJ = J/s * MJ/J * hr *s/hr
  ener_consumed = pumping_power*duration*3600*1/1000000 + ener_consumed_refrig #J/s * hr * s/hr * MJ/J = MJ
  A -= BOG_loss
  money = ener_consumed*start_electricity_price #MJ*$/MJ = $
  #money from electricity
  G_emission = ener_consumed*0.2778*CO2e_start*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  return money, ener_consumed, G_emission, A, BOG_loss

def chem_storage_at_port_A(A,B,C,D,E,F):
  number_of_storage = math.ceil(A/liquid_chem_density[B]/storage_volume[B]) #kg/(kg/m3)/m3
  local_BOR_storage = dBOR_dT[B]*(start_local_temperature-25)+BOR_land_storage[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = A*local_BOR_storage*storage_time #kg =  kg* %/day * day
  A -= BOG_loss
  storage_area = 4*np.pi*(storage_radius[B]**2)*number_of_storage  #m2, here storage size depends on the initial H2 weight (10,000 kg for example)
  thermal_resist = tank_metal_thickness/metal_thermal_conduct + tank_insulator_thickness/insulator_thermal_conduct #m/(W/(m K)) = (m2 K)/W, ref [3] eqn  6& 7
  OHTC = 1/thermal_resist #W/(m2 K), ref [3] eqn 5
  # print('storage tank OHTC:',round(OHTC,3))
  heat_required = OHTC*storage_area*(start_local_temperature+273-20) #W = W/(m2 K)* m2 * K, ref [3] eqn 16
  ener_consumed = (heat_required/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*86400*storage_time #MJ = J/s * MJ/J * s/day   ref [3] eqn 1
  money = ener_consumed*start_electricity_price #$ = MJ*$/MJ
  G_emission = ener_consumed*0.2778*CO2e_start*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778

  ##recirculation
  if C == 2:
    ##1) reliq BOG
    if E == 1:
      usable_BOG = BOG_loss*BOG_recirculation_storage*0.01 #kg
      BOG_flowrate = usable_BOG/storage_time*1/24 #kg/hr = kg/days *days/hr
      reliq_ener_required = liquification_data_fitting(BOG_flowrate)/(EIM_liquefication/100)  #MJ/kg
      reliq_ener_consumed = reliq_ener_required*usable_BOG #MJ/kg*kg = MJ
      ener_consumed = reliq_ener_consumed + ener_consumed
      money = ener_consumed*start_electricity_price
      BOG_loss = BOG_loss*(1-BOG_recirculation_storage*0.01)
      G_emission = ener_consumed*0.2778*CO2e_start*0.001 + BOG_loss * GWP_chem[B]
      A += usable_BOG


    ##2) reuse BOG to produce electricity from fuel cells
    elif E == 2:
      usable_BOG = BOG_loss*BOG_recirculation_storage*0.01 #kg
      usable_ener = usable_BOG * fuel_cell_eff * EIM_fuel_cell/100 * LHV_chem[B] #MJ = kg * MJ/kg
      ener_consumed = ener_consumed - usable_ener
      if ener_consumed < 0:
        ener_consumed = 0
      else:
        False
      money = ener_consumed*start_electricity_price
      BOG_loss = BOG_loss*(1-BOG_recirculation_storage*0.01)
      G_emission = ener_consumed*0.2778*CO2e_start*0.001 + BOG_loss * GWP_chem[B] ##kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g
    else:
      False
  else:
    False
  return money, ener_consumed, G_emission, A, BOG_loss

def chem_loading_to_ship(A,B,C,D,E,F):
  duration = A/(V_flowrate[B])/number_of_cryo_pump_load_ship_port_A #hr = kg/(kg/m3 * m3/hr)
  local_BOR_loading = dBOR_dT[B]*(start_local_temperature-25)+BOR_loading[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = local_BOR_loading*(1/24)*duration*A  #kg = %/day * day/hr * hr * kg
  pumping_power = liquid_chem_density[B]*V_flowrate[B]*(1/3600)*head_pump*9.8/(367*pump_power_factor) #W: kg/m3 * m3/hr * hr/s * m * m/s^2 = kg/s*m2/s2 = W, ref [3] eqn 11
  q_pipe = 2*np.pi*ss_therm_cond*pipe_length*(start_local_temperature-(-253))/(2.3*np.log10((pipe_inner_D+2*pipe_thick)/pipe_inner_D))    #W, ref [3], equ 17 and table 5
  ener_consumed_refrig = (q_pipe/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*duration*3600  #MJ = J/s * MJ/J * hr * s/hr
  ener_consumed = pumping_power*duration*3600*1/1000000 + ener_consumed_refrig #J/s * hr * s/hr * MJ/J = MJ
  A -= BOG_loss
  money = ener_consumed*start_electricity_price #MJ*$/MJ = $
  #money from electricity
  G_emission = ener_consumed*0.2778*CO2e_start*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  return money, ener_consumed, G_emission, A, BOG_loss

def port_to_port(A,B,C,D,E,F):
  #####   Method 1, calculation based on ref [3]
  # LF = (avg_ship_speed/max_ship_speed)**3  #ref [3] equ 12
  # avg_shaft_power = LF*engine_power #MW, ref [3] equ 13
  # total_load = avg_shaft_power/propul_eff + hotel_load #MW, ref [3] equ 14
  # ener_consumed_power = total_load*3600*port_to_port_duration #MW * s/hr * hr  = MJ
  # ##refrig
  T_avg = (start_local_temperature+end_local_temperature)/2
  # thermal_resist = ship_tank_metal_thickness/metal_thermal_conduct + ship_tank_insulator_thickness/insulator_thermal_conduct #m/(W/(m K)) = (m2 K)/W, ref [3] eqn  6& 7
  # OHTC = 1/thermal_resist #W/(m2 K), ref [3] eqn 5
  # #print('vessel OHTC:',round(OHTC,3))
  heat_required = OHTC_ship[B]*storage_area*(T_avg+273-20)*ship_number_of_tanks #W = W/(m2 K)* m2 * K, ref [3] eqn 16
  ener_consumed_refrig = (heat_required/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*3600*port_to_port_duration/ship_engine_eff #MJ = J/s * MJ/J * s/hr   ref [3] eqn 1
  refrig_money = (ener_consumed_refrig/(HHV_heavy_fuel*propul_eff*EIM_ship_eff/100))*(1/1000)*marine_shipping_price #MJ/(MJ/kg)* metric ton/kg * $/metric tone


  #####   Method 2, calculation based on fuel consumption rate
  marine_fuel_needed = ship_fuel_consumption * 1/1.609 * port_to_port_dis  #metric ton = metric ton/mi * mi/km * km (at speed 18 knots)
  money = marine_fuel_needed * marine_shipping_price + refrig_money #$ = metric ton * $/metric ton
  ener_consumed = marine_fuel_needed * 1000 * HHV_heavy_fuel + ener_consumed_refrig #MJ = metric ton * kg/metric ton * MJ/kg
  local_BOR_transportation = dBOR_dT[B]*(T_avg-25)+BOR_ship_trans[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = local_BOR_transportation*(1/24)*port_to_port_duration*A #kg = %/day * day/hr *hr * kg
  A -= BOG_loss
  G_emission = ener_consumed/(HHV_heavy_fuel*heavy_fuel_density)*CO2e_heavy_fuel + BOG_loss*GWP_chem[B] #kg CO2 = MJ/(MJ/kg * kg/gallon) * kgCO2/gallon

  ##recirculation
  if C == 2:
    #reliq
    if F == 1:
      usable_BOG = BOG_loss*BOG_recirculation_mati_trans*0.01 #kg
      BOG_flowrate = usable_BOG/port_to_port_duration #kg/hr = kg/min *min/hr
      reliq_ener_required = liquification_data_fitting(BOG_flowrate)/(EIM_liquefication/100)  #MJ/kg
      reliq_ener_consumed = reliq_ener_required*usable_BOG #MJ/kg*kg = MJ
      # reliq_ener_consumed_extra = (heat_required/COP_reliq)/1000000*60*duration_A_to_port*number_of_trucks
      ener_consumed = reliq_ener_consumed + ener_consumed #+ reliq_ener_consumed_extra
      reliq_money = (reliq_ener_consumed/(HHV_heavy_fuel*propul_eff*EIM_ship_eff/100))/heavy_fuel_density*marine_shipping_price #$ = MJ/(MJ/kg)/(kg/gal) * ($/gal)
      money += reliq_money
      A += usable_BOG
      BOG_loss = BOG_loss*(1-BOG_recirculation_mati_trans*0.01)
      G_emission_energy = ener_consumed/HHV_heavy_fuel/heavy_fuel_density*CO2e_heavy_fuel #MJ/(MJ/kg)/(kg/gal) * kgCO2/gal
      G_emission = G_emission_energy + BOG_loss*GWP_chem[B] #kgCO2 = kgCO2 + kgH2 * kgCO2/kgH2
    #fuel cell for refrig
    elif F == 2:
      usable_BOG = BOG_loss*BOG_recirculation_mati_trans*0.01 #kg
      usable_ener = usable_BOG * fuel_cell_eff * EIM_fuel_cell/100 * LHV_chem[B]  #MJ = kg * MJ/kg
      energy_save = ener_consumed_refrig - usable_ener
      refrig_money_new = (energy_save/(HHV_heavy_fuel*propul_eff*EIM_ship_eff/100))/heavy_fuel_density*marine_shipping_price
      if energy_save < 0:
        energy_save = 0
        refrig_money_new = 0
        money = marine_fuel_needed * marine_shipping_price
        ener_consumed = marine_fuel_needed * 1000 * HHV_heavy_fuel
      else:
        money = marine_fuel_needed * marine_shipping_price + refrig_money_new
        ener_consumed = marine_fuel_needed * 1000 * HHV_heavy_fuel + energy_save
      BOG_loss = BOG_loss*(1-BOG_recirculation_mati_trans*0.01)
      G_emission_energy = ener_consumed/HHV_heavy_fuel/heavy_fuel_density*CO2e_heavy_fuel #MJ/(MJ/kg)/(kg/gal) * kgCO2/gal
      G_emission = G_emission_energy + BOG_loss*GWP_chem[B] #kgCO2 = kgCO2 + kgH2 * kgCO2/kgH2
    else:
      False
  else:
    False

  return money, ener_consumed, G_emission, A, BOG_loss

def chem_unloading_from_ship(A,B,C,D,E,F):
  duration = A/(V_flowrate[B])/number_of_cryo_pump_load_storage_port_B #s = kg/(kg/m3 * m3/hr)* s/hr
  local_BOR_unloading = dBOR_dT[B]*(end_local_temperature-25)+BOR_unloading[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = local_BOR_unloading*(1/24)*duration*A   #!!!!kg = %/day * day/s *s * kg
  pumping_power = liquid_chem_density[B]*V_flowrate[B]*(1/3600)*head_pump*9.8/(367*pump_power_factor) #891 W: kg/m3 * m3/hr * hr/s * m * m/s^2 = kg/s*m2/s2 = W, ref [3] eqn 11
  q_pipe = 2*np.pi*ss_therm_cond*pipe_length*(end_local_temperature-(-253))/(2.3*np.log10((pipe_inner_D+2*pipe_thick)/pipe_inner_D))    #W, ref [3], equ 17 and table 5
  ener_consumed_refrig = (q_pipe/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*duration*3600  #MJ = J/s * MJ/J * hr * s/hr
  ener_consumed = pumping_power*duration*1/1000000*3600 + ener_consumed_refrig #J/s * hr * s/hr * MJ/J = MJ
  A -= BOG_loss
  money = ener_consumed*end_electricity_price #MJ*$/MJ = $
  #money from electricity
  G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  return money, ener_consumed, G_emission, A, BOG_loss

def chem_storage_at_port_B(A,B,C,D,E,F):
  number_of_storage = math.ceil(A/liquid_chem_density[B]/storage_volume[B]) #kg/(kg/m3)/m3
  local_BOR_storage = dBOR_dT[B]*(end_local_temperature-25)+BOR_land_storage[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = A*local_BOR_storage*storage_time #kg =  kg* %/day * day, ref [2], 3 days for storage
  A -= BOG_loss
  storage_area = 4*np.pi*(storage_radius[B]**2)*number_of_storage  #m2, here storage size depends on the initial H2 weight (10,000 kg for example)
  thermal_resist = tank_metal_thickness/metal_thermal_conduct + tank_insulator_thickness/insulator_thermal_conduct #m/(W/(m K)) = (m2 K)/W, ref [3] eqn  6& 7
  OHTC = 1/thermal_resist #W/(m2 K), ref [3] eqn 5
  heat_required = OHTC*storage_area*(end_local_temperature+273-20) #W = W/(m2 K)* m2 * K, ref [3] eqn 16
  ener_consumed = (heat_required/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*86400*storage_time #MJ = J/s * MJ/J * s/day * day  ref [3] eqn 1
  money = ener_consumed*end_electricity_price #$ = MJ*$/MJ
  G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778

  ##recirculation
  if C == 2:
    ##1) reliq BOG
    if E == 1:
      usable_BOG = BOG_loss*BOG_recirculation_storage*0.01 #kg
      BOG_flowrate = usable_BOG/storage_time*1/24 #kg/hr = kg/days *days/hr
      reliq_ener_required = liquification_data_fitting(BOG_flowrate)/(EIM_liquefication/100)  #MJ/kg
      reliq_ener_consumed = reliq_ener_required*usable_BOG #MJ/kg*kg = MJ
      ener_consumed = reliq_ener_consumed + ener_consumed
      money = ener_consumed*end_electricity_price
      BOG_loss = BOG_loss*(1-BOG_recirculation_storage*0.01)
      G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss * GWP_chem[B]
      A += usable_BOG


    ##2) reuse BOG to produce electricity from fuel cells
    elif E == 2:
      usable_BOG = BOG_loss*BOG_recirculation_storage*0.01 #kg
      usable_ener = usable_BOG * fuel_cell_eff * EIM_fuel_cell/100 * LHV_chem[B] #MJ = kg * MJ/kg
      ener_consumed = ener_consumed - usable_ener
      if ener_consumed < 0:
        ener_consumed = 0
      else:
        False
      money = ener_consumed*end_electricity_price
      BOG_loss = BOG_loss*(1-BOG_recirculation_storage*0.01)
      G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss * GWP_chem[B] ##kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g
    else:
      False
  else:
    False
  return money, ener_consumed, G_emission, A, BOG_loss

def port_B_unloading_from_storage(A,B,C,D,E,F):
  duration = A/(V_flowrate[B])/number_of_cryo_pump_load_truck_port_B #hr = kg/(kg/m3 * m3/hr)
  local_BOR_unloading = dBOR_dT[B]*(end_local_temperature-25)+BOR_unloading[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = local_BOR_unloading*(1/24)*duration*A  #kg = %/day * day/hr *hr * kg
  pumping_power = liquid_chem_density[B]*V_flowrate[B]*(1/3600)*head_pump*9.8/(367*pump_power_factor) #W: kg/m3 * m3/hr * hr/s * m * m/s^2 = kg/s*m2/s2 = W, ref [3] eqn 11
  q_pipe = 2*np.pi*ss_therm_cond*pipe_length*(end_local_temperature-(-253))/(2.3*np.log10((pipe_inner_D+2*pipe_thick)/pipe_inner_D))    #W, ref [3], equ 17 and table 5
  ener_consumed_refrig = (q_pipe/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*duration*3600
  ener_consumed = pumping_power*duration*3600*1/1000000 + ener_consumed_refrig #J/s * hr * s/hr * MJ/J = MJ
  A -= BOG_loss
  money = ener_consumed*end_electricity_price #MJ*$/MJ = $
  #money from electricity
  G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  return money, ener_consumed, G_emission, A, BOG_loss

def port_B_to_site_B(A,B,C,D,E,F):
  global number_of_trucks
  truck_energy_consumed = road_delivery_ener[B]*HHV_chem[B]  # %/km * MJ/kg = MJ/(kg km), ref [1] fig 6
  
  number_of_trucks = A/chem_in_truck_weight[B]
  # print('To deliver this amount of LH2,',round(number_of_trucks,0),'number of trucks is required for in-land transportation.')
  trans_energy_required = truck_energy_consumed*distance_port_to_B*A #MJ/(kg km)*#*km*kg = MJ
  diesel_money = trans_energy_required/HHV_diesel/diesel_density*diesel_price #MJ/(MJ/kg)/(kg/gal) * ($/gal)
  ### Refrig
  
  ### Refrig
  storage_area = 2*np.pi*truck_tank_radius*truck_tank_length  #m2, here storage size depends on the initial H2 weight (10,000 kg for example)
  thermal_resist = truck_tank_metal_thickness/metal_thermal_conduct + truck_tank_insulator_thickness/insulator_thermal_conduct #m/(W/(m K)) = (m2 K)/W, ref [3] eqn  6& 7
  OHTC = 1/thermal_resist #W/(m2 K), ref [3] eqn 5
  heat_required = OHTC*storage_area*(end_local_temperature+273-20) #W = W/(m2 K)* m2 * K, ref [3] eqn 16
  refrig_ener_consumed = (heat_required/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*60*duration_port_to_B*number_of_trucks #MJ = J/s * MJ/J * s/min   ref [3] eqn 1
  ###
  local_BOR_truck_trans = dBOR_dT[B]*(end_local_temperature-25)+BOR_truck_trans[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = A*local_BOR_truck_trans/24/60*duration_port_to_B #kg =  kg* %/day * day/hr * hr/min * min)
  refrig_money = (refrig_ener_consumed/(HHV_diesel*diesel_engine_eff))/diesel_density*diesel_price #[MJ/(MJ/kg)]/(kg/gal) *$/gal

  money = diesel_money + refrig_money
  total_energy = trans_energy_required + refrig_ener_consumed
  A -= BOG_loss
  G_emission_energy = total_energy/HHV_diesel/diesel_density*CO2e_diesel #MJ/(MJ/kg)/(kg/gal) * kgCO2/gal
  G_emission = G_emission_energy + BOG_loss*GWP_chem[B] #kgCO2 = kgCO2 + kgH2 * kgCO2/kgH2

  ##recirculation
  if C == 2:
    ##1) reliq BOG
    if D == 1:
      usable_BOG = BOG_loss*BOG_recirculation_truck*0.01 #kg
      BOG_flowrate = usable_BOG/duration_port_to_B*60 #kg/hr = kg/min *min/hr
      reliq_ener_required = liquification_data_fitting(BOG_flowrate)/(EIM_liquefication/100)  #MJ/kg
      reliq_ener_consumed = reliq_ener_required*usable_BOG #MJ/kg*kg = MJ
      # reliq_ener_consumed_extra = (heat_required/COP_reliq)/1000000*60*duration_A_to_port*number_of_trucks
      total_energy = reliq_ener_consumed + trans_energy_required + refrig_ener_consumed #+ reliq_ener_consumed_extra
      reliq_money = (reliq_ener_consumed/(HHV_diesel*diesel_engine_eff*EIM_truck_eff/100))/diesel_density*diesel_price #$ = MJ/(MJ/kg)/(kg/gal) * ($/gal)
      money = diesel_money + reliq_money + refrig_money
      A += usable_BOG
      BOG_loss = BOG_loss*(1-BOG_recirculation_truck*0.01)
      G_emission_energy = total_energy/HHV_diesel/diesel_density*CO2e_diesel #MJ/(MJ/kg)/(kg/gal) * kgCO2/gal
      G_emission = G_emission_energy + BOG_loss*GWP_chem[B] #kgCO2 = kgCO2 + kgH2 * kgCO2/kgH2

    ##2) reuse BOG to produce electricity from fuel cells
    elif D == 2:
      usable_BOG = BOG_loss*BOG_recirculation_truck*0.01 #kg
      usable_ener = usable_BOG * fuel_cell_eff * EIM_fuel_cell/100 * LHV_chem[B] #MJ = kg * MJ/kg
      ener_consumed = refrig_ener_consumed - usable_ener
      refrig_money_save = (usable_ener/(HHV_diesel*diesel_engine_eff*EIM_truck_eff/100))/diesel_density*diesel_price
      money_save = refrig_money - refrig_money_save
      if ener_consumed < 0:
        ener_consumed = 0
        money = diesel_money
        total_energy = trans_energy_required
      else:
        money = diesel_money + money_save
        total_energy = trans_energy_required + ener_consumed
      BOG_loss = BOG_loss*(1-BOG_recirculation_truck*0.01)
      G_emission_energy = total_energy/HHV_diesel/diesel_density*CO2e_diesel #MJ/(MJ/kg)/(kg/gal) * kgCO2/gal
      G_emission = G_emission_energy + BOG_loss*GWP_chem[B] #kgCO2 = kgCO2 + kgH2 * kgCO2/kgH2
    else:
      False
  else:
    False
  return money, total_energy, G_emission, A, BOG_loss

def chem_site_B_unloading_from_truck(A,B,C,D,E,F):
  duration = A/(V_flowrate[B])/number_of_cryo_pump_load_storage_site_B #hr = kg/(kg/m3 * m3/hr)
  local_BOR_unloading = dBOR_dT[B]*(end_local_temperature-25)+BOR_unloading[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = local_BOR_unloading*(1/24)*duration*A  #!!!!kg = %/day * day/hr *hr * kg
  pumping_power = liquid_chem_density[B]*V_flowrate[B]*(1/3600)*head_pump*9.8/(367*pump_power_factor) #W: kg/m3 * m3/hr * hr/s * m * m/s^2 = kg/s*m2/s2 = W, ref [3] eqn 11
  q_pipe = 2*np.pi*ss_therm_cond*pipe_length*(end_local_temperature-(-253))/(2.3*np.log10((pipe_inner_D+2*pipe_thick)/pipe_inner_D))    #W, ref [3], equ 17 and table 5
  ener_consumed_refrig = (q_pipe/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*duration*3600
  ener_consumed = pumping_power*duration*3600*1/1000000 + ener_consumed_refrig #J/s * hr * s/hr * MJ/J = MJ
  A -= BOG_loss
  money = ener_consumed*end_electricity_price #MJ*$/MJ = $
  #money from electricity
  G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  return money, ener_consumed, G_emission, A, BOG_loss

def chem_storage_at_site_B(A,B,C,D,E,F):
  number_of_storage = math.ceil(A/liquid_chem_density[B]/storage_volume[B]) #kg/(kg/m3)/m3
  local_BOR_storage = dBOR_dT[B]*(end_local_temperature-25)+BOR_land_storage[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = A*local_BOR_storage*storage_time #kg =  kg* %/day * day, ref [2], 3 days for storage
  A -= BOG_loss
  storage_area = 4*np.pi*(storage_radius[B]**2)*number_of_storage  #m2, here storage size depends on the initial H2 weight (10,000 kg for example)
  thermal_resist = tank_metal_thickness/metal_thermal_conduct + tank_insulator_thickness/insulator_thermal_conduct #m/(W/(m K)) = (m2 K)/W, ref [3] eqn  6& 7
  OHTC = 1/thermal_resist #W/(m2 K), ref [3] eqn 5
  heat_required = OHTC*storage_area*(end_local_temperature+273-20) #W = W/(m2 K)* m2 * K, ref [3] eqn 16
  ener_consumed = (heat_required/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*86400*storage_time #MJ = J/s * MJ/J * s/day   ref [3] eqn 1
  money = ener_consumed*end_electricity_price #$ = MJ*$/MJ
  G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778

  ##recirculation
  if C == 2:
    ##1) reliq BOG
    if E == 1:
      usable_BOG = BOG_loss*BOG_recirculation_storage*0.01 #kg
      BOG_flowrate = usable_BOG/storage_time*1/24 #kg/hr = kg/days *days/hr
      reliq_ener_required = liquification_data_fitting(BOG_flowrate)/(EIM_liquefication/100)  #MJ/kg
      reliq_ener_consumed = reliq_ener_required*usable_BOG #MJ/kg*kg = MJ
      ener_consumed = reliq_ener_consumed + ener_consumed
      money = ener_consumed*end_electricity_price
      BOG_loss = BOG_loss*(1-BOG_recirculation_storage*0.01)
      G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss * GWP_chem[B]
      A += usable_BOG


    ##2) reuse BOG to produce electricity from fuel cells
    elif E == 2:
      usable_BOG = BOG_loss*BOG_recirculation_storage*0.01 #kg
      usable_ener = usable_BOG * fuel_cell_eff * EIM_fuel_cell/100 * LHV_chem[B] #MJ = kg * MJ/kg
      ener_consumed = ener_consumed - usable_ener
      if ener_consumed < 0:
        ener_consumed = 0
      else:
        False
      money = ener_consumed*end_electricity_price
      BOG_loss = BOG_loss*(1-BOG_recirculation_storage*0.01)
      G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss * GWP_chem[B] ##kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g
    else:
      False
  else:
    False
  return money, ener_consumed, G_emission, A, BOG_loss

def chem_unloading_from_site_B(A,B,C,D,E,F):   #to consumer
  duration = A/(V_flowrate[B])/number_of_cryo_pump_load_storage_site_B #hr = kg/(kg/m3 * m3/hr)
  local_BOR_unloading = dBOR_dT[B]*(end_local_temperature-25)+BOR_unloading[B]  #dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
  BOG_loss = local_BOR_unloading*(1/24)*duration*A  #!!!!kg = %/day * day/hr *hr * kg
  pumping_power = liquid_chem_density[B]*V_flowrate[B]*(1/3600)*head_pump*9.8/(367*pump_power_factor) #W: kg/m3 * m3/hr * hr/s * m * m/s^2 = kg/s*m2/s2 = W, ref [3] eqn 11
  q_pipe = 2*np.pi*ss_therm_cond*pipe_length*(end_local_temperature-(-253))/(2.3*np.log10((pipe_inner_D+2*pipe_thick)/pipe_inner_D))    #W, ref [3], equ 17 and table 5
  ener_consumed_refrig = (q_pipe/(COP_refrig[B]*EIM_refrig_eff/100))/1000000*duration*3600
  ener_consumed = pumping_power*duration*3600*1/1000000 + ener_consumed_refrig #J/s * hr * s/hr * MJ/J = MJ
  A -= BOG_loss
  money = ener_consumed*end_electricity_price #MJ*$/MJ = $
  #money from electricity
  G_emission = ener_consumed*0.2778*CO2e_end*0.001 + BOG_loss*GWP_chem[B] #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  return money, ener_consumed, G_emission, A, BOG_loss

### PH2 section:
def PH2_pressurization_at_site_A(A,B,C,D,E,F):
  #compressor
  PH2_density = A/(PH2_storage_V*numbers_of_PH2_storage_at_start)  #kg/m3 = kg / (m3*#)
  PH2_pressure = PH2_pressure_fnc(PH2_density)   #bar = kg/m3 / kg/m3 * 1 bar
  compress_energy = multistage_compress(PH2_pressure)*A/multistage_eff #MJ/kg H2 * kg = MJ
  
  money = start_electricity_price*compress_energy #$/MJ*MJ  need compressor stations?
  G_emission = compress_energy*0.2778*CO2e_start*0.001 #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  leak_loss = 0
  print('H2 pressure at pressurization process at site A (bar): ',PH2_pressure)
  return money, compress_energy, G_emission, A, leak_loss

def PH2_site_A_to_port_A(A,B,C,D,E,F):
  PH2_density = A/(PH2_storage_V*numbers_of_PH2_storage_at_start)  #kg/m3 = kg / (m3*#)
  PH2_pressure = PH2_pressure_fnc(PH2_density)   #bar = kg/m3 / kg/m3 * 1 bar

  L = straight_dis_start_A_to_port
  kine_vis = kinematic_viscosity_PH2(PH2_pressure)
  Re = compressor_velocity*pipeline_diameter/kine_vis
  f_D = solve_colebrook(Re, epsilon, pipeline_diameter)
  P_drop = L*f_D*PH2_density*compressor_velocity**2/(2*pipeline_diameter)/100000  #bar, m*kg/m3*m2/s2/m = kg/m-s2 = Pa, Darcy-Weisbach equation
  ####  not using
  pumping_power = P_drop*100000*compressor_velocity*np.pi*pipeline_diameter**2/4  #Pa * m3/s = W, ref [1] eqn 4
  pipe_area = np.pi*pipeline_diameter**2/4
  duration = A/PH2_density/pipe_area/compressor_velocity  #s = kg/(kg/m3 * m2 * m/s)
  pumping_ener = pumping_power*duration/1000000  #MJ = W * s * 1/1000000
  print('pumping energy: ',pumping_ener)
  ####
  ener_consumed = PH2_transport_energy(L)*A  #MJ, ref [1] fig. 7
  final_P_PH2 = PH2_pressure - P_drop

  final_PH2_density = gas_chem_density[B]
  A_final = final_PH2_density*PH2_storage_V*numbers_of_PH2_storage
  trans_loss = A-A_final
  money = start_electricity_price*ener_consumed #$/MJ*MJ  start_electricity_price might be wrong if the port is in different state from start location
  G_emission = ener_consumed*0.2778*CO2e_start*0.001 #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  print('pressure drop (bar): ',P_drop)
  print('final pressure at port A (bar): ',final_P_PH2)
  return money, ener_consumed, G_emission, A_final, trans_loss

def port_A_liquification(A,B,C,D,E,F):  
  LH2_energy_required = liquification_data_fitting(LH2_plant_capacity)/(EIM_liquefication/100) #MJ/kg
  LH2_ener_consumed = LH2_energy_required*A #MJ/kg*kg = MJ
  LH2_money = LH2_ener_consumed*start_port_electricity_price #MJ*$/MJ = $
  G_emission = LH2_ener_consumed*0.2778*CO2e_start*0.001 #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  BOG_loss = 0.016*A  #ed in Table 5. A hydrogen loss of 1.6 % was assumed during liquefaction in ref [11] page 21
 
  return LH2_money, LH2_ener_consumed, G_emission, A, BOG_loss

def H2_pressurization_at_port_B(A,B,C,D,E,F):
  Q_latent = latent_H_H2 * A #MJ = MJ/kg *kg, vaporizer
  Q_sensible = A*specific_heat_H2*(300-20)  #MJ = kg * MJ/(kg K) * K

  PH2_density = A/(PH2_storage_V*numbers_of_PH2_storage)  #kg/m3 = kg / (m3*#)
  PH2_pressure = PH2_pressure_fnc(PH2_density)   #bar = kg/m3 / kg/m3 * 1 bar
  compress_energy = multistage_compress(PH2_pressure)*A/multistage_eff #MJ/kg H2 * kg = MJ
  
  ener_consumed  = compress_energy + Q_latent + Q_sensible
  money = end_port_electricity_price*ener_consumed #$/MJ*MJ  need compressor stations?
  G_emission = ener_consumed*0.2778*CO2e_end*0.001 #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  leak_loss = 0
  print('H2 pressure at pressurization process at port B (bar): ',PH2_pressure)
  return money, ener_consumed, G_emission, A, leak_loss

def PH2_port_B_to_site_B(A,B,C,D,E,F):
  PH2_density = PH2_density_fnc(target_pressure_site_B)   #kg/m3
  numbers_of_PH2_storage = A/(PH2_density*PH2_storage_V)  # number = kg/(kg/m3 * m3)


  L = straight_dis_port_B_to_end
  kine_vis = kinematic_viscosity_PH2(PH2_pressure)
  Re = compressor_velocity*pipeline_diameter/kine_vis
  f_D = solve_colebrook(Re, epsilon, pipeline_diameter)
  P_drop = L*f_D*PH2_density*compressor_velocity**2/(2*pipeline_diameter)/100000  #bar, m*kg/m3*m2/s2/m = kg/m-s2 = Pa, Darcy-Weisbach equation
  ####  not using
  pumping_power = P_drop*100000*compressor_velocity*np.pi*pipeline_diameter**2/4  #Pa * m3/s = W, ref [1] eqn 4
  pipe_area = np.pi*pipeline_diameter**2/4
  duration = A/PH2_density/pipe_area/compressor_velocity  #s = kg/(kg/m3 * m2 * m/s)
  pumping_ener = pumping_power*duration/1000000  #MJ = W * s * 1/1000000
  print('pumping energy: ',pumping_ener)
  ####
  ener_consumed = PH2_transport_energy(L)*A  #MJ, ref [1] fig. 7
  final_P_PH2 = PH2_pressure - P_drop

  final_PH2_density = PH2_density_fnc(final_P_PH2)
  A_final = final_PH2_density*PH2_storage_V*numbers_of_PH2_storage
  trans_loss = A-A_final
  money = end_port_electricity_price*ener_consumed #$/MJ*MJ  start_electricity_price might be wrong if the port is in different state from start location
  G_emission = ener_consumed*0.2778*CO2e_end*0.001 #kgCO2 = MJ* kWh/MJ * gCO2/kWh* kg/g, kWh=MJ×0.2778
  print('pressure drop (bar): ',P_drop)
  print('final pressure at site B (bar): ',final_P_PH2)
  return money, ener_consumed, G_emission, A_final, trans_loss

def PH2_storage_at_site_B(A,B,C,D,E,F):
  PH2_density = A/(PH2_storage_V*numbers_of_PH2_storage)  #kg/m3 = kg / (m3*#)
  PH2_pressure = PH2_pressure_fnc(PH2_density)   #bar = kg/m3 / kg/m3 * 1 bar
  G_emission = 0
  money = 0
  ener_consumed = 0
  BOG_loss = 0
  return money, ener_consumed, G_emission, A, BOG_loss


# %% # Optimization method
# Optimization method
import warnings
import sys

# Suppress warnings (if any are causing the unwanted output)
warnings.filterwarnings('ignore')

# Redirect stdout to suppress print outputs
#class HiddenPrints:
#    def __enter__(self):
#        self._original_stdout = sys.stdout
#        sys.stdout = open('/dev/null', 'w')

 #   def __exit__(self, exc_type, exc_val, exc_tb):
 #       sys.stdout.close()
 #       sys.stdout = self._original_stdout


def optimization_chem_weight(A):
    funcs = [site_A_chem_production, site_A_chem_liquification, chem_site_A_loading_to_truck,
             site_A_to_port_A, port_A_unloading_to_storage, chem_storage_at_port_A, chem_loading_to_ship]

    X = A[0]  # Use A[0] since minimize expects an array
    R = Y = Z = S = T = 0.0
    for i, func in enumerate(funcs):
        # with HiddenPrints():  # Hide print output inside function calls
            X, Y, Z, R, S = func(X, user_define[1], user_define[2], user_define[3],user_define[4],user_define[5])
            if i ==6:
                return abs(X - target_weight)
    return abs(X - target_weight)

def optimization_PH2_weight(A):
    funcs = [site_A_chem_production, PH2_pressurization_at_site_A, PH2_site_A_to_port_A,
            port_A_liquification, chem_loading_to_ship]

    X = A[0]  # Use A[0] since minimize expects an array
    R = Y = Z = S = T = 0.0
    for i, func in enumerate(funcs):
        # with HiddenPrints():  # Hide print output inside function calls
            X, Y, Z, R, S, T = func(X, user_define[1], user_define[2], user_define[3],user_define[4],user_define[5])
            if i ==4:
                return abs(X - target_weight)
    return abs(X - target_weight)

def constraint(A):
    return target_weight - A[0]  # A[0] is LH2_weight in this context

con = {'type': 'ineq', 'fun': constraint}

# Set bounds to ensure positive weight
bounds = [(0, None)]

# Use a more appropriate initial guess


#with HiddenPrints():  # Hide print output during optimization
target_weight = ship_tank_volume * liquid_chem_density[int(fuel_type)] * 0.98 * ship_number_of_tanks  # kg, ref [3] section 2.1:  the filling limit is defined as 98% for ships cargo tank.
initial_guess = [target_weight/2]

result = minimize(optimization_chem_weight, initial_guess, method='L-BFGS-B', bounds=bounds, constraints=[con])

chem_weight = result.x[0]
user_define[0] = target_weight

# %% # Final results
# Final results

def total_chem(A,B,C,D,E,F): #LH2 throughout the whole transportation process
  funcs = [site_A_chem_production, site_A_chem_liquification, chem_site_A_loading_to_truck,
           site_A_to_port_A, port_A_unloading_to_storage, chem_storage_at_port_A, chem_loading_to_ship,
           port_to_port, \
           chem_unloading_from_ship, chem_storage_at_port_B, port_B_unloading_from_storage, port_B_to_site_B,
           chem_site_B_unloading_from_truck, chem_storage_at_site_B, chem_unloading_from_site_B]
  R = A
  X = Y = Z = S = total_money = total_ener_consumed = total_G_emission = 0.0
  data = []
  for func in funcs:
    X,Y,Z,R,S = func(R,B,C,D,E,F)[:]
    result = X,Y,Z,R,S
    # print(f"Function: {func.__name__}, Result: {tuple(round(num,1) for num in result)}")

    # data.append(result)
    data.append((func.__name__, tuple("{:.3e}".format(num) for num in result)))
    total_money += X
    total_ener_consumed += Y
    total_G_emission += Z
  total_result = [total_money, total_ener_consumed, total_G_emission, R]
  data.append(("TOTAL", tuple("{:.3e}".format(num) for num in total_result)))

  return total_result, data

def total_PH2(A,B,C,D,E,F):  #LH2 obly during port to port, others are pressurized

  funcs = [site_A_chem_production, PH2_pressurization_at_site_A, PH2_site_A_to_port_A, 
            port_A_liquification, chem_loading_to_ship,
            port_to_port, chem_unloading_from_ship, chem_storage_at_port_B, 
            H2_pressurization_at_port_B, PH2_port_B_to_site_B , PH2_storage_at_site_B]
  R = A
  X = Y = Z = S = total_money = total_ener_consumed = total_G_emission = 0.0
  data = []
  for func in funcs:
    X,Y,Z,R,S = func(R,B,C,D,E)[:]
    result = X,Y,Z,R,S
    # print(f"Function: {func.__name__}, Result: {tuple(round(num,1) for num in result)}")

    # data.append(result)
    data.append((func.__name__, tuple("{:.3e}".format(num) for num in result)))
    total_money += X
    total_ener_consumed += Y
    total_G_emission += Z
  total_result = [total_money, total_ener_consumed, total_G_emission, R]
  data.append(("TOTAL", tuple("{:.3e}".format(num) for num in total_result)))

  return total_result, data


total_results, data = total_chem(chem_weight, user_define[1],user_define[2], user_define[3],user_define[4],user_define[5])


from tabulate import tabulate
headers = ["Function", "cost ($)", "energy consumed (MJ)", "eCO2 emission(kg)", "total LH2 (kg)", "Boiloff loss (kg)"]
table = [(func, *tuple("{:.2e}".format(float(num)) for num in result)) for func, result in data]

print(tabulate(table, headers=headers, tablefmt="grid"))
print('')
# print('total cost: $',round(total_results[0]), '  energy consumed:',round(total_results[1]), 'MJ  ', 'CO2e:', round(total_results[2]), 'kg  ', 'initial & final LH2:', round(LH2_weight), '&' , round(total_results[3]), 'kg')
#unit(total_money: $, total_ener_consumed: MJ, total_G_emission: kg CO2e, final_H2_weight: kg)

chem_cost = total_results[0]/total_results[3]
chem_energy = total_results[1]/total_results[3]
chem_CO2e = total_results[2]/total_results[3]

table_data = [["Cost ($/kg chemical)", round(chem_cost, 2)],
              ["Energy (MJ/kg chemical)", round(chem_energy, 2)],
              ["Emission (kg CO2/kg chemical)", round(chem_CO2e, 2)]]

print(tabulate(table_data, headers=["Metric", "Value"], tablefmt="grid"))
# print(f'Cost: ${round(LH2_cost,2)}/kg LH2;',  f'Energy: {round(LH2_energy,2)} MJ/kg LH2;', f'Emission: {round(LH2_CO2e,2)} kg CO2/kg LH2.')
print('shipping tank storage area (m2): ', round(storage_area,2))


# %% # Write to csv file
# Write to csv file
import csv
import re
import os
comment = input("Enter a comment for the filename: ")
google_drive_path = os.path.expanduser("~/Google Drive/My Drive/Research/H2transLCA/study cases/")
save_directory = os.path.join(google_drive_path, "CSVFiles")
os.makedirs(save_directory, exist_ok=True)
def create_filename(start, end, comment):
    # Remove non-alphanumeric characters and replace spaces with underscores
    start = re.sub(r'[^\w\s]', '', start).replace(' ', '_')
    end = re.sub(r'[^\w\s]', '', end).replace(' ', '_')
    comment = re.sub(r'[^\w\s]', '', comment).replace(' ', '_')
    return f"{start}_to_{end}_{comment}.csv"
filename = create_filename(start, end, comment)
full_file_path = os.path.join(save_directory, filename)

with open(full_file_path, 'w', newline='') as file:
    writer = csv.writer(file)
    
    # Write the table
    writer.writerow(headers)
    for row in table:
        writer.writerow(row)
    
    # Write a blank row as a separator
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    writer.writerows(table_data)
    writer.writerow([])
    writer.writerow(['user define: (H2 weight & recirculation tpyes)',user_define])
    writer.writerow(['start: ', start])
    writer.writerow(['end: ', end])
    writer.writerow(['start local temperature: ', start_local_temperature])
    writer.writerow(['start electricity price ($/MJ): ', start_electricity_price])
    writer.writerow(['end electricity price ($/MJ): ', end_electricity_price])
    writer.writerow(['end local temperature (C): ',end_local_temperature])
    writer.writerow(['distance (km) and duration from site A to port A: ',start_to_port[0],start_to_port[1]])
    writer.writerow(['port name: ', start_port[0]])
    writer.writerow(['port name: ', end_port[0]])
    writer.writerow(['distance port to port (km): ',round(port_to_port_dis,2)])
    writer.writerow(['distance and duration from port B to site B: ',port_to_end[0],port_to_end[1]])
    writer.writerow(['ship tank volume: (m3)',ship_tank_volume])
    writer.writerow(['ship number of tanks: ',ship_number_of_tanks])
    writer.writerow(['number of cryo pump load truck port A: ',number_of_cryo_pump_load_truck_site_A])
    writer.writerow(['number of trucks at site A: ', round(number_of_trucks,0)])
    writer.writerow(['BOG (%)',BOG_recirculation_storage])
    writer.writerow(['L H2 plant capacity: (kg/hr)', LH2_plant_capacity])
    writer.writerow(['eCO2 at start location: (gCO2/kWh)', CO2e_start])
    writer.writerow(['eCO2 at end location: (gCO2/kWh)', CO2e_end])
    writer.writerow(['shipping tank shape (1 for capsule, 2 for spherical): ', ship_tank_shape])
    writer.writerow(['shipping tank radius (m): ', ship_tank_radius])
    writer.writerow(['shipping tank surface area (m2): ', storage_area])
    # Write other information
    # for info in other_info:
    #     writer.writerow([info])

print(f"File saved as: {full_file_path}")
# %%# Backup function 


"""# Economic evaluation

total annual cost =

# Backup codes

SeaRoutes bans me from their database as they only provide very limited access API key.
"""

# def port_to_port(port_start, port_end):
#    base_endpoint_route = "https://api.searoutes.com/route/v2/sea/"
#    coordinate = f"{port_start[1]},{port_start[0]};{port_end[1]},{port_end[0]}"
#    params = {
#     "continuousCoordinates": "true",
#     "allowIceAreas": "false",
#     "avoidHRA": "false",
#     "avoidSeca": "false"
#    }


#    coor_encoded = urllib.parse.quote(coordinate, safe='')
#    params_encoded = urlencode(params)
#    route_endpoint = f'{base_endpoint_route}{coor_encoded}?{params_encoded}'

#    headers = {
#     "accept": "application/json",
#     "x-api-key": api_key_searoutes
#    }

#    r = requests.get(route_endpoint, headers=headers)
#    output = r.json()
#    return output

# sea_route = port_to_port(start_port[1:], end_port[1:])
# print(sea_route)
# coordinates_list = [feature['geometry']['coordinates'] for feature in sea_route['features']]

# feature_properties = sea_route['features'][0]['properties']

# sea_route_distance = feature_properties['distance']*1e-3/1.609
# sea_route_duration = feature_properties['duration']/3.6e+6
# #sea_route_speed = round(distance,2)/round(duration,2)

# #print(start_port)
# #print(end_port[0])

# A = 0

# def X(A,B):
#     A = float(A)
#     A -= 10
#     B = 5
#     return A, B

# def Y(A,B):
#     A = float(A)
#     A -= 10
#     B = 2
#     return A, B

# def Z(A,B):
#     A = float(A)
#     A -= 10
#     B = 3
#     return A, B

# def total(A, B):
#     funcs = [X, Y, Z]
#     result = (A, B)  # Initialize result as a tuple

#     for func in funcs:
#         A, _ = result  # Extract the current value of A
#         result = func(A, B)  # Pass only A to the function

#     return result

# print(total(10, 2))

# def objective(A):
#     funcs = [X, Y]  # We only want to apply X and Y
#     result = (A, 2)  # Initialize result as a tuple

#     for i, func in enumerate(funcs):
#         A, _ = result  # Extract the current value of A
#         result = func(A, 2)  # Pass only A to the function
#         if i == 1:  # After applying Y (which is the second function)
#             return abs(result[0] - 100)  # Minimize the difference from 100

# # Perform the optimization
# result = minimize_scalar(objective)

# optimal_A = result.x

# print(optimal_A)

print('')
input("Press Enter to exit...")



# %% Testing



# Define origin and destination points:
origin = [0.3515625, 50.064191736659104]
destination = [117.42187500000001, 39.36827914916014]

# # Calculate the route in nautical miles:
# route = sr.searoute(origin, destination, units="nm")
# print(route.geometry['coordinates'])
# print(route.properties['length'])
# print(route.properties['units'])
# # Print the route length in nautical miles:
# print("{:.1f} {}".format(route.properties['length'], route.properties['units']))

api_key_openEI = 't7Nk4EbjPTARVzDRKRLhR5kfpvGuPey1FRbfwOae'
import requests
import pandas as pd

def get_electricity_price(api_key, zone):
    """
    Fetches electricity price for a specific zone from the ElectricityMap API.
    
    Args:
        api_key (str): Your ElectricityMap API key.
        zone (str): The zone code (e.g., 'DE' for Germany, 'SA' for Saudi Arabia).
    
    Returns:
        dict: The electricity price data for the requested zone.
    """
    
    # Define the API endpoint
    url = f"https://api.electricitymap.org/v3/zone/{zone}"

    # Headers with the authentication token
    headers = {
        'auth-token': api_key,
    }

    try:
        # Make the API request
        response = requests.get(url, headers=headers)
        
        # Check for successful response
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to retrieve data: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Example usage
api_key = 'uM85ii6sssSEi'  # Replace with your valid ElectricityMap API key
zone = 'DE'  # Replace with zone code ('DE' for Germany, 'SA' for Saudi Arabia)
electricity_price_data = get_electricity_price(api_key, zone)

# Print the electricity price data
if electricity_price_data:
    print(electricity_price_data)





# def get_electricity_price_data():
#     # Corrected OEDI API endpoint for utility rates
#     url = "https://developer.nrel.gov/api/utility_rates/v3.json"  # OEDI's utility rate API

#     # API parameters, replace 'YOUR_OEDI_API_KEY' with your actual API key
#     params = {
#         'api_key': api_key_openEI,  # Replace with your valid API key
#         'lat': 36.7783,    # Latitude (e.g., New York City)
#         'lon': -119.4179   # Longitude (e.g., New York City)
#     }

#     try:
#         # Make the API request
#         response = requests.get(url, params=params)
        
#         # Check if the request was successful
#         if response.status_code == 200:
#             # Parse the response JSON content
#             data = response.json()
            
#             # Convert the 'outputs' data to a pandas DataFrame
#             df = pd.json_normalize(data['outputs'])
            
#             # Display the data (first few rows)
#             print(df.head())
#         else:
#             print(f"Failed to retrieve data: {response.status_code} - {response.text}")
    
#     except Exception as e:
#         print(f"An error occurred: {e}")

# # Example usage
# get_electricity_price_data()

# %%
