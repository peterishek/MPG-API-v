# import requests
# import math
# import time
# from .models import FuelStop, Vehicle


# class Optimizer:
#     """
#     Fuel route optimizer using OSRM for routing and lazy geocoding
#     Geocodes stops in start, end, and intermediate states along the route
#     Calculates optimal fuel stops based on distance, cost, and reachability
#     """
    
#     def __init__(self, vehicle):
#         self.vehicle = vehicle
#         self.OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
#         self.NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
#         self.REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
#         self.fuel_stops_dict = self._load_fuel_stops_dict()
    
#     def _load_fuel_stops_dict(self):
#         """Load all fuel stops into dictionary for O(1) lookup"""
#         stops_dict = {}
#         for stop in FuelStop.objects.all():
#             stops_dict[stop.id] = stop.to_dict()
#         return stops_dict
    
#     # ==================== GEOCODING ====================
    
#     def geocode_address(self, address):
#         """Geocode an address (start/end location)"""
#         try:
#             time.sleep(1)
            
#             params = {
#                 'q': address,
#                 'format': 'json',
#                 'timeout': 10
#             }
            
#             print(f"    📍 Geocoding: {address}")
            
#             response = requests.get(
#                 self.NOMINATIM_URL, 
#                 params=params, 
#                 timeout=10,
#                 headers={'User-Agent': 'FuelOptimizer/1.0'}
#             )
            
#             if response.status_code != 200:
#                 raise Exception(f"HTTP {response.status_code}")
            
#             data = response.json()
            
#             if not data or len(data) == 0:
#                 raise ValueError(f"Address not found: {address}")
            
#             result = data[0]
#             lat = float(result['lat'])
#             lng = float(result['lon'])
            
#             print(f"       ✅ Found: ({lat:.4f}, {lng:.4f})")
#             return (lat, lng)
        
#         except Exception as e:
#             print(f"       ❌ Error: {str(e)}")
#             raise Exception(f"Geocoding failed for '{address}': {str(e)}")
    
#     def extract_states_from_locations(self, start_location, end_location):
#         """Extract state abbreviations from start and end locations"""
#         print(f"\n📍 Extracting states from start/end locations...")
        
#         states = set()
        
#         for location in [start_location, end_location]:
#             parts = location.split(',')
#             if len(parts) >= 2:
#                 state = parts[-1].strip().upper()
#                 if len(state) == 2:
#                     states.add(state)
#                     print(f"    ✅ Extracted: {state}")
        
#         if len(states) == 0:
#             raise ValueError("Could not extract states from locations")
        
#         return states
    
#     def extract_intermediate_states(self, route_coords):
#         """Extract states along route by reverse geocoding sampled points"""
#         print(f"\n🗺️  Extracting intermediate states from route path...")
        
#         intermediate_states = set()
        
#         if not route_coords or len(route_coords) < 2:
#             print(f"    ⚠️  Route too short for intermediate detection")
#             return intermediate_states
        
#         # Sample ~12 points evenly along route
#         sample_step = max(1, len(route_coords) // 12)
#         sampled_points = route_coords[sample_step:-sample_step:sample_step]
        
#         print(f"    Sampling {len(sampled_points)} points along route...")
        
#         for idx, (lat, lng) in enumerate(sampled_points):
#             try:
#                 response = requests.get(
#                     self.REVERSE_URL,
#                     params={
#                         'lat': lat,
#                         'lon': lng,
#                         'format': 'json',
#                         'addressdetails': 1,
#                         'zoom': 10
#                     },
#                     headers={'User-Agent': 'FuelOptimizer/1.0'},
#                     timeout=10
#                 )
                
#                 if response.status_code == 200:
#                     address_data = response.json().get('address', {})
#                     state_code = address_data.get('state_code') or address_data.get('state')
                    
#                     if state_code and len(state_code.upper()) == 2:
#                         intermediate_states.add(state_code.upper())
#                         print(f"    ✅ Point {idx+1}: {state_code.upper()}")
                
#                 time.sleep(1)
            
#             except Exception as error:
#                 print(f"    ⚠️  Point {idx+1} failed: {str(error)}")
#                 continue
        
#         if intermediate_states:
#             print(f"    📍 Intermediate states: {', '.join(sorted(intermediate_states))}")
        
#         return intermediate_states
    
#     def geocode_stops_for_states(self, states):
#         """Geocode stops in the specified states"""
#         print(f"\n🔄 Geocoding stops in states: {', '.join(sorted(states))}...")
        
#         stops_to_geocode = FuelStop.objects.filter(
#             latitude=0.0,
#             longitude=0.0,
#             state__in=states
#         ).values('city', 'state').distinct().order_by('state', 'city')
        
#         geocoded_count = 0
#         failed_count = 0
#         total_cities = stops_to_geocode.count()
        
#         print(f"    Found {total_cities} cities needing geocoding...")
        
#         for i, city_data in enumerate(stops_to_geocode, 1):
#             city = city_data['city']
#             state = city_data['state']
            
#             try:
#                 params = {
#                     'city': city,
#                     'state': state,
#                     'country': 'USA',
#                     'format': 'json',
#                     'timeout': 10
#                 }
                
#                 response = requests.get(
#                     self.NOMINATIM_URL, 
#                     params=params, 
#                     timeout=10,
#                     headers={'User-Agent': 'FuelOptimizer/1.0'}
#                 )
                
#                 if response.status_code != 200:
#                     failed_count += 1
#                     time.sleep(2)
#                     continue
                
#                 data = response.json()
                
#                 if data:
#                     result = data[0]
#                     lat = float(result['lat'])
#                     lng = float(result['lon'])
                    
#                     updated = FuelStop.objects.filter(
#                         city=city,
#                         state=state,
#                         latitude=0.0
#                     ).update(latitude=lat, longitude=lng)
                    
#                     if i % 5 == 0 or i == total_cities:
#                         print(f"    [{i}/{total_cities}] ✅ {city}, {state}")
                    
#                     geocoded_count += updated
#                 else:
#                     failed_count += 1
                
#                 time.sleep(1.5)
            
#             except Exception as e:
#                 failed_count += 1
#                 time.sleep(2)
        
#         print(f"    ✅ Geocoded {geocoded_count} stops, Failed: {failed_count}")
#         self.fuel_stops_dict = self._load_fuel_stops_dict()
    
#     # ==================== ROUTING ====================
    
#     def get_route(self, start_coords, end_coords):
#         """Get route from OSRM"""
#         try:
#             coordinates = f"{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
            
#             url = f"{self.OSRM_URL}/{coordinates}"
#             params = {'overview': 'full', 'geometries': 'geojson'}
            
#             print(f"    📍 Getting route from OSRM...")
            
#             response = requests.get(url, params=params, timeout=30)
#             data = response.json()
            
#             if data['code'] != 'Ok':
#                 raise Exception(f"OSRM error: {data['code']}")
            
#             if not data.get('routes') or len(data['routes']) == 0:
#                 raise Exception("No route found in OSRM response")
            
#             route = data['routes'][0]
#             coordinates_list = []
            
#             if 'geometry' in route and route['geometry']:
#                 geometry = route['geometry']
                
#                 if isinstance(geometry, dict) and 'coordinates' in geometry:
#                     coordinates_list = geometry['coordinates']
#                     coordinates_list = [[c[1], c[0]] for c in coordinates_list]
#                     print(f"    ✅ Extracted {len(coordinates_list)} route points")
#                 elif isinstance(geometry, str):
#                     coordinates_list = self._decode_polyline(geometry)
            
#             if not coordinates_list:
#                 print(f"    ⚠️  No coordinates extracted, using start/end fallback")
#                 coordinates_list = [start_coords, end_coords]
            
#             distance_miles = route['distance'] / 1609.34
#             duration_seconds = route['duration']
            
#             print(f"    ✅ Route: {distance_miles:.1f} miles")
            
#             return {
#                 'distance_miles': distance_miles,
#                 'duration_seconds': duration_seconds,
#                 'coordinates': coordinates_list,
#                 'geometry': route.get('geometry', {})
#             }
        
#         except Exception as e:
#             print(f"    ❌ Route error: {str(e)}")
#             raise Exception(f"Route calculation failed: {str(e)}")
    
#     def _decode_polyline(self, encoded):
#         """Decode OSRM polyline format (fallback)"""
#         return [[0, 0]]
    
#     # ==================== DISTANCE CALCULATIONS ====================
    
#     def haversine_distance(self, lat1, lng1, lat2, lng2):
#         """Calculate distance between two coordinates in miles"""
#         R = 3959
        
#         lat1_rad = math.radians(lat1)
#         lat2_rad = math.radians(lat2)
#         delta_lat = math.radians(lat2 - lat1)
#         delta_lng = math.radians(lng2 - lng1)
        
#         a = (math.sin(delta_lat/2) ** 2 + 
#              math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2) ** 2)
#         c = 2 * math.asin(math.sqrt(a))
        
#         return R * c
    
#     def find_stops_in_range(self, lat, lng, max_distance):
#         """Find all fuel stops within max_distance from current position"""
#         nearby_stops = []
        
#         for stop in FuelStop.objects.all():
#             if stop.latitude == 0.0 or stop.longitude == 0.0:
#                 continue
            
#             distance = self.haversine_distance(lat, lng, stop.latitude, stop.longitude)
            
#             if distance <= max_distance:
#                 stop_dict = stop.to_dict()
#                 stop_dict['distance_from_current'] = distance
#                 nearby_stops.append(stop_dict)
        
#         return nearby_stops
    
#     # ==================== STOP SELECTION ====================
    
#     def find_optimal_stop(self, fuel_stops_in_range, leg_distance):
#         """
#         Select optimal fuel stop using decision logic
#         Formula for cost: (distance_to_next_stop / mpg) * price_per_gallon
#         """
#         if not fuel_stops_in_range:
#             return None, 0, "No stops in range"
        
#         closest_stop = min(fuel_stops_in_range, key=lambda s: s['distance_from_current'])
#         cheapest_stop = min(fuel_stops_in_range, key=lambda s: s['price_per_gallon'])
        
#         if closest_stop['id'] == cheapest_stop['id']:
#             optimal_stop = closest_stop
#             reason = "Same location (closest and cheapest)"
#         else:
#             remaining_from_closest = leg_distance - closest_stop['distance_from_current']
#             remaining_from_cheapest = leg_distance - cheapest_stop['distance_from_current']
            

#             max_reach = getattr(self.vehicle, 'max_range', self.vehicle.available_tank_range)

#             closest_reachable = remaining_from_closest <= self.vehicle.available_tank_range
#             cheapest_reachable = remaining_from_cheapest <= self.vehicle.available_tank_range
            
#             if closest_reachable and cheapest_reachable:
#                 optimal_stop = cheapest_stop
#                 reason = "Cheapest option (both reachable)"
#             elif closest_reachable:
#                 optimal_stop = closest_stop
#                 reason = "Closest is only reachable option"
#             elif cheapest_reachable:
#                 optimal_stop = cheapest_stop
#                 reason = "Cheapest is only reachable option"
#             else:
#                 optimal_stop = cheapest_stop
#                 reason = "Default to cheapest"
        
#         # Calculate cost: (leg_distance / mpg) * price
#         fuel_cost = (leg_distance / self.vehicle.mpg) * optimal_stop['price_per_gallon']
        
#         return optimal_stop, fuel_cost, reason
    
#     # ==================== MAIN OPTIMIZATION ====================
    
#     # def optimize_route(self, start_location, end_location):
#     #     """Main optimization function"""
#     #     try:
#     #         print(f"\n🚀 Starting route optimization:")
#     #         print(f"    From: {start_location}")
#     #         print(f"    To: {end_location}")
#     #         print(f"    Vehicle: {self.vehicle.name}")
            
#     #         # Step 1: Extract states from locations
#     #         states_to_geocode = self.extract_states_from_locations(start_location, end_location)
            
#     #         # Step 2: Geocode start and end
#     #         print("\n📍 Step 2: Geocoding start and end locations...")
#     #         start_coords = self.geocode_address(start_location)
#     #         end_coords = self.geocode_address(end_location)
            
#     #         # Step 3: Get route from OSRM
#     #         print("\n🗺️  Step 3: Calculating route...")
#     #         route_data = self.get_route(start_coords, end_coords)
#     #         total_distance = route_data['distance_miles']
#     #         route_coords = route_data['coordinates']
            
#     #         # Step 3.5: Extract intermediate states
#     #         intermediate_states = self.extract_intermediate_states(route_coords)
#     #         states_to_geocode.update(intermediate_states)
#     #         print(f"\n    📍 Total states: {', '.join(sorted(states_to_geocode))}")
            
#     #         # Step 4: Geocode all states
#     #         self.geocode_stops_for_states(states_to_geocode)
            
#     #         # Step 5: Find optimal fuel stops
#     #         print("\n⛽ Step 5: Finding optimal fuel stops...")
#     #         fuel_stops = []
#     #         current_position = start_coords
#     #         remaining_distance = total_distance
#     #         distance_traveled = 0
#     #         stop_number = 1
            
#     #         while remaining_distance > self.vehicle.available_tank_range:
#     #             print(f"\n    Stop {stop_number}: {remaining_distance:.1f}mi remaining")
                
#     #             stops_in_range = self.find_stops_in_range(
#     #                 current_position[0],
#     #                 current_position[1],
#     #                 self.vehicle.available_tank_range
#     #             )
                
#     #             if not stops_in_range:
#     #                 print(f"       ⚠️  No stops in range!")
#     #                 break
                
#     #             optimal_stop, fuel_cost, reason = self.find_optimal_stop(
#     #                 stops_in_range,
#     #                 remaining_distance
#     #             )
                
#     #             if not optimal_stop:
#     #                 break
                
#     #             print(f"       ✅ {optimal_stop['name']} - ${fuel_cost:.2f}")
                
#     #             fuel_stops.append({
#     #                 'stop_number': stop_number,
#     #                 'stop': optimal_stop,
#     #                 'distance_from_start': distance_traveled,
#     #                 'distance_to_next': remaining_distance,
#     #                 'fuel_cost_here': fuel_cost,
#     #                 'selection_reason': reason
#     #             })
                
#     #             current_position = (optimal_stop['latitude'], optimal_stop['longitude'])
#     #             distance_traveled += self.vehicle.available_tank_range  # ✅ USE VEHICLE RANGE
#     #             remaining_distance -= self.vehicle.available_tank_range  # ✅ USE VEHICLE RANGE
#     #             stop_number += 1
            
#     #         # Step 6: Calculate final leg
#     #         print(f"\n💰 Step 6: Final leg cost...")
            
#     #         if fuel_stops:
#     #             last_stop_price = fuel_stops[-1]['stop']['price_per_gallon']
#     #         else:
#     #             stops_near_start = self.find_stops_in_range(
#     #                 start_coords[0],
#     #                 start_coords[1],
#     #                 self.vehicle.available_tank_range  # ✅ USE VEHICLE RANGE
#     #             )
                
#     #             if stops_near_start:
#     #                 optimal_start_stop, _, _ = self.find_optimal_stop(
#     #                     stops_near_start,
#     #                     remaining_distance
#     #                 )
#     #                 last_stop_price = optimal_start_stop['price_per_gallon'] if optimal_start_stop else 3.50
#     #             else:
#     #                 last_stop_price = 3.50
            
#     #         final_leg_cost = (remaining_distance / self.vehicle.mpg) * last_stop_price
#     #         total_fuel_cost = sum([s['fuel_cost_here'] for s in fuel_stops]) + final_leg_cost
            
#     #         print(f"    ✅ Total cost: ${total_fuel_cost:.2f}")
            
#     #         return {
#     #             'total_distance': total_distance,
#     #             'total_fuel_cost': total_fuel_cost,
#     #             'start_location': start_location,
#     #             'end_location': end_location,
#     #             'start_lat': start_coords[0],
#     #             'start_lng': start_coords[1],
#     #             'end_lat': end_coords[0],
#     #             'end_lng': end_coords[1],
#     #             'route_coordinates': route_coords,
#     #             'fuel_stops': fuel_stops,
#     #         }
        
#     #     except Exception as e:
#     #         print(f"\n❌ Optimization error: {str(e)}")
#     #         import traceback
#     #         traceback.print_exc()
#     #         raise

#     def optimize_route(self, start_location, end_location):
#         """Main optimization function - Improved for long routes + map support"""
#         try:
#             print(f"\n🚀 Starting route optimization:")
#             print(f"    From: {start_location}")
#             print(f"    To: {end_location}")
#             print(f"    Vehicle: {self.vehicle.name}")
            
#             # Step 1: Extract states
#             states_to_geocode = self.extract_states_from_locations(start_location, end_location)
            
#             # Step 2: Geocode start and end
#             print("\n📍 Step 2: Geocoding start and end locations...")
#             start_coords = self.geocode_address(start_location)
#             end_coords = self.geocode_address(end_location)
            
#             # Step 3: Get full route from OSRM (for map + planning)
#             print("\n🗺️  Step 3: Calculating route...")
#             route_data = self.get_route(start_coords, end_coords)
#             total_distance = route_data['distance_miles']
#             route_coords = route_data['coordinates']
            
#             # Step 3.5: Better intermediate states detection
#             intermediate_states = self.extract_intermediate_states(route_coords)
#             states_to_geocode.update(intermediate_states)
#             print(f"\n    📍 Total states: {', '.join(sorted(states_to_geocode))}")
            
#             # Step 4: Geocode stops in all relevant states
#             self.geocode_stops_for_states(states_to_geocode)
            
#             # ==================== IMPROVED STOP PLANNING ====================
#             print("\n⛽ Step 5: Planning fuel stops along route...")
#             fuel_stops = []
#             current_position = start_coords
#             remaining_distance = total_distance
#             distance_traveled = 0
#             stop_number = 1
            
#             max_range = getattr(self.vehicle, 'max_range', 600)
            
#             while remaining_distance > self.vehicle.available_tank_range * 0.8:
#                 print(f"\n    Stop {stop_number}: {remaining_distance:.1f} mi remaining")
                
#                 # Search radius: current fuel for first stop, then full tank planning
#                 search_radius = self.vehicle.available_tank_range if stop_number == 1 else max_range * 0.85
                
#                 stops_in_range = self.find_stops_in_range(
#                     current_position[0], current_position[1], search_radius
#                 )
                
#                 if not stops_in_range:
#                     print("       ⚠️  No stops in range!")
#                     break
                
#                 leg_distance = min(remaining_distance, max_range * 0.9)
                
#                 optimal_stop, fuel_cost, reason = self.find_optimal_stop(
#                     stops_in_range, leg_distance
#                 )
                
#                 if not optimal_stop:
#                     break
                
#                 print(f"       ✅ {optimal_stop.get('name', 'Stop')} - ${fuel_cost:.2f} ({reason})")
                
#                 fuel_stops.append({
#                     'stop_number': stop_number,
#                     'stop': optimal_stop,                    # full stop dict
#                     'distance_from_start': round(distance_traveled, 1),
#                     'distance_to_next': round(remaining_distance, 1),   # or distance_to_destination
#                     'distance_traveled': round(leg_distance, 1),        # for frontend
#                     'fuel_cost_here': round(fuel_cost, 2),
#                     'selection_reason': reason,
#                     'leg_distance': round(leg_distance, 1)
#                 })
                
                
#                 distance_traveled += leg_distance
#                 remaining_distance -= leg_distance
#                 current_position = (optimal_stop['latitude'], optimal_stop['longitude'])
#                 stop_number += 1
            
#             # Step 6: Final leg cost
#             print(f"\n💰 Step 6: Final leg cost...")
#             last_stop_price = fuel_stops[-1]['stop']['price_per_gallon'] if fuel_stops else 3.50
            
#             final_leg_cost = (remaining_distance / self.vehicle.mpg) * last_stop_price
#             total_fuel_cost = sum(s['fuel_cost_here'] for s in fuel_stops) + final_leg_cost
            
#             print(f"    ✅ Total estimated fuel cost: ${total_fuel_cost:.2f}")
            
#             # Return data optimized for frontend + map
#             return {
#                 'total_distance': round(total_distance, 1),
#                 'total_fuel_cost': round(total_fuel_cost, 2),
#                 'cost_per_mile': round(total_fuel_cost / total_distance, 4) if total_distance > 0 else 0,
#                 'start_location': start_location,
#                 'end_location': end_location,
#                 'start_lat': start_coords[0],
#                 'start_lng': start_coords[1],
#                 'end_lat': end_coords[0],
#                 'end_lng': end_coords[1],
#                 'route_coordinates': route_coords,           # ← Full route for map
#                 'fuel_stops': fuel_stops,
#                 'states_traversed': sorted(list(states_to_geocode)),
#                 'no_stops_needed': len(fuel_stops) == 0 and remaining_distance <= self.vehicle.available_tank_range
#             }
        
#         except Exception as e:
#             print(f"\n❌ Optimization error: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             raise


import requests
import math
import time
from .models import FuelStop, Vehicle


class Optimizer:
    """
    Fuel route optimizer using OSRM for routing and lazy geocoding.
    Tracks vehicle range thresholds to pull relevant path corridors safely.
    """
    
    STATE_MAP = {
        'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR', 'CALIFORNIA': 'CA',
        'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE', 'FLORIDA': 'FL', 'GEORGIA': 'GA',
        'HAWAII': 'HI', 'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
        'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
        'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS', 'MISSOURI': 'MO',
        'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ',
        'NEW MEXICO': 'NM', 'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH',
        'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
        'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT', 'VERMONT': 'VT',
        'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY'
    }

    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
        self.NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
        self.REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
        self.fuel_stops_dict = self._load_fuel_stops_dict()
    
    def _load_fuel_stops_dict(self):
        stops_dict = {}
        for stop in FuelStop.objects.all():
            stops_dict[stop.id] = stop.to_dict()
        return stops_dict
    
    # ==================== GEOCODING ====================
    
    def geocode_address(self, address):
        try:
            time.sleep(1)
            params = {'q': address, 'format': 'json', 'timeout': 10}
            print(f"    📍 Geocoding: {address}")
            
            response = requests.get(
                self.NOMINATIM_URL, 
                params=params, 
                timeout=10,
                headers={'User-Agent': 'FuelOptimizer/1.0'}
            )
            data = response.json()
            if not data:
                raise ValueError(f"Address not found: {address}")
            
            result = data[0]
            return (float(result['lat']), float(result['lon']))
        except Exception as e:
            raise Exception(f"Geocoding failed for '{address}': {str(e)}")
    
    def extract_states_from_locations(self, start_location, end_location):
        print(f"\n📍 Extracting states from start/end locations...")
        states = set()
        for location in [start_location, end_location]:
            parts = location.split(',')
            if len(parts) >= 2:
                raw_state = parts[-1].strip().upper()
                if len(raw_state) == 2:
                    states.add(raw_state)
                elif raw_state in self.STATE_MAP:
                    states.add(self.STATE_MAP[raw_state])
        return states
    
    def extract_intermediate_states(self, route_coords):
        print(f"\n🗺️  Extracting intermediate states from route path...")
        intermediate_states = set()
        if not route_coords or len(route_coords) < 2:
            return intermediate_states
        
        sample_step = max(1, len(route_coords) // 15)
        sampled_points = route_coords[sample_step:-sample_step:sample_step]
        
        for idx, (lat, lng) in enumerate(sampled_points):
            try:
                response = requests.get(
                    self.REVERSE_URL,
                    params={'lat': lat, 'lon': lng, 'format': 'json', 'addressdetails': 1, 'zoom': 10},
                    headers={'User-Agent': 'FuelOptimizer/1.0'},
                    timeout=10
                )
                if response.status_code == 200:
                    address_data = response.json().get('address', {})
                    state_raw = address_data.get('state', '').upper().strip()
                    state_code_raw = address_data.get('state_code', '').upper().strip()
                    
                    if len(state_code_raw) == 2:
                        intermediate_states.add(state_code_raw)
                    elif len(state_raw) == 2:
                        intermediate_states.add(state_raw)
                    elif state_raw in self.STATE_MAP:
                        intermediate_states.add(self.STATE_MAP[state_raw])
                time.sleep(1.1)
            except Exception:
                continue
        return intermediate_states
    
    def geocode_stops_for_states(self, states):
        """Geocode missing database entries with real-time logging for all targets"""
        stops_to_geocode = FuelStop.objects.filter(
            latitude=0.0, longitude=0.0, state__in=states
        ).values('city', 'state').distinct().order_by('state', 'city')
        
        total_cities = stops_to_geocode.count()
        geocoded_count = 0
        failed_count = 0
        
        if total_cities == 0:
            print("    ✅ All stations in these states already possess coordinate bounds data.")
            return

        print(f"\n🔄 Real-time geocoding missing records for states: {', '.join(sorted(states))}...")
        print(f"    Found {total_cities} unique city targets needing coordinate bounds updates...")
        
        for i, city_data in enumerate(stops_to_geocode, 1):
            city = city_data['city']
            state = city_data['state']
            try:
                params = {'city': city, 'state': state, 'country': 'USA', 'format': 'json', 'timeout': 10}
                response = requests.get(
                    self.NOMINATIM_URL, 
                    params=params, 
                    timeout=10, 
                    headers={'User-Agent': 'FuelOptimizer/1.0'}
                )
                
                if response.status_code == 200 and response.json():
                    result = response.json()[0]
                    lat, lng = float(result['lat']), float(result['lon'])
                    
                    updated = FuelStop.objects.filter(
                        city=city, state=state, latitude=0.0
                    ).update(latitude=lat, longitude=lng)
                    
                    geocoded_count += updated
                    print(f"    [{i}/{total_cities}] ✅ {city}, {state}")
                else:
                    failed_count += 1
                    print(f"    [{i}/{total_cities}] ❌ No results for {city}, {state}")
                    
                time.sleep(1.2)  # Maintain Nominatim rate limits safely
            except Exception as e:
                failed_count += 1
                print(f"    [{i}/{total_cities}] ❌ Error geocoding {city}, {state}: {str(e)}")
                time.sleep(1.5)
                
        print(f"\n    ✅ Geocoding Phase Complete. Updated: {geocoded_count}, Failed/Skipped: {failed_count}")
        self.fuel_stops_dict = self._load_fuel_stops_dict()
    
    # ==================== ROUTING ====================
    
    def get_route(self, start_coords, end_coords):
        try:
            coordinates = f"{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
            url = f"{self.OSRM_URL}/{coordinates}"
            response = requests.get(url, params={'overview': 'full', 'geometries': 'geojson'}, timeout=30)
            data = response.json()
            
            if data['code'] != 'Ok':
                raise Exception(f"OSRM error: {data['code']}")
            
            route = data['routes'][0]
            coordinates_list = [[c[1], c[0]] for c in route['geometry']['coordinates']]
            return {
                'distance_miles': route['distance'] / 1609.34,
                'duration_seconds': route['duration'],
                'coordinates': coordinates_list
            }
        except Exception as e:
            raise Exception(f"Route calculation failed: {str(e)}")
    
    def haversine_distance(self, lat1, lng1, lat2, lng2):
        R = 3959
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        a = (math.sin(delta_lat/2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2) ** 2)
        return R * (2 * math.asin(math.sqrt(a)))

    # ==================== PATH CORRIDOR SEARCH ====================

    def find_stops_along_corridor(self, route_coords, cumulative_distances, current_dist, max_window, states):
        valid_stops = []
        target_min_dist = current_dist + 10.0  
        target_max_dist = current_dist + max_window
        
        active_segment_points = []
        for idx, dist in enumerate(cumulative_distances):
            if target_min_dist <= dist <= target_max_dist:
                active_segment_points.append((route_coords[idx], dist))
        
        if not active_segment_points:
            return valid_stops

        candidate_stops = FuelStop.objects.filter(state__in=states, latitude__gt=0.0).exclude(price_per_gallon=0.0)
        
        for stop in candidate_stops:
            min_offset_distance = float('inf')
            matched_distance_from_start = 0
            
            for pt, path_dist in active_segment_points:
                offset = self.haversine_distance(stop.latitude, stop.longitude, pt[0], pt[1])
                if offset < min_offset_distance:
                    min_offset_distance = offset
                    matched_distance_from_start = path_dist
            
            if min_offset_distance <= 3.0 and matched_distance_from_start > (current_dist + 15.0):
                stop_dict = stop.to_dict()
                stop_dict['distance_from_current'] = matched_distance_from_start - current_dist
                stop_dict['absolute_distance_from_start'] = matched_distance_from_start
                valid_stops.append(stop_dict)
                
        return valid_stops

    def find_optimal_stop(self, fuel_stops_in_range, leg_distance):
        if not fuel_stops_in_range:
            return None, 0, "No stops in range"
        
        closest_stop = min(fuel_stops_in_range, key=lambda s: s['distance_from_current'])
        cheapest_stop = min(fuel_stops_in_range, key=lambda s: s['price_per_gallon'])
        
        if closest_stop['id'] == cheapest_stop['id']:
            optimal_stop = closest_stop
            reason = "Same location (closest and cheapest)"
        else:
            remaining_from_closest = leg_distance - closest_stop['distance_from_current']
            remaining_from_cheapest = leg_distance - cheapest_stop['distance_from_current']
            
            closest_reachable = remaining_from_closest <= self.vehicle.available_tank_range
            cheapest_reachable = remaining_from_cheapest <= self.vehicle.available_tank_range
            
            if closest_reachable and cheapest_reachable:
                optimal_stop = cheapest_stop
                reason = "Cheapest option (both reachable)"
            elif closest_reachable:
                optimal_stop = closest_stop
                reason = "Closest is only reachable option"
            else:
                optimal_stop = cheapest_stop
                reason = "Default to cheapest"
        
        fuel_cost = (leg_distance / self.vehicle.mpg) * optimal_stop['price_per_gallon']
        return optimal_stop, fuel_cost, reason
    
    # ==================== MAIN OPTIMIZATION ====================
    
    def optimize_route(self, start_location, end_location):
        try:
            print(f"\n🚀 Starting highway path route optimization:")
            states_to_geocode = self.extract_states_from_locations(start_location, end_location)
            
            start_coords = self.geocode_address(start_location)
            end_coords = self.geocode_address(end_location)
            
            route_data = self.get_route(start_coords, end_coords)
            total_distance = route_data['distance_miles']
            route_coords = route_data['coordinates']
            
            cumulative_distances = [0]
            for i in range(1, len(route_coords)):
                chunk_dist = self.haversine_distance(route_coords[i-1][0], route_coords[i-1][1], route_coords[i][0], route_coords[i][1])
                cumulative_distances.append(cumulative_distances[-1] + chunk_dist)
            
            intermediate_states = self.extract_intermediate_states(route_coords)
            states_to_geocode.update(intermediate_states)
            print(f"    📍 All Detected States: {', '.join(sorted(states_to_geocode))}")
            
            self.geocode_stops_for_states(states_to_geocode)
            
            print("\n⛽ Planning fuel stops down the highway path...")
            fuel_stops = []
            current_dist_milestone = 0
            stop_number = 1
            
            max_range = getattr(self.vehicle, 'tank_range_max', self.vehicle.available_tank_range)
            
            while (total_distance - current_dist_milestone) > self.vehicle.available_tank_range * 0.85:
                print(f"    Stop {stop_number}: {(total_distance - current_dist_milestone):.1f} mi remaining")
                
                search_window = self.vehicle.available_tank_range if stop_number == 1 else max_range * 0.85
                
                stops_in_range = self.find_stops_along_corridor(
                    route_coords, cumulative_distances, 
                    current_dist_milestone, search_window, states_to_geocode
                )
                
                if not stops_in_range:
                    print("       ⚠️  No forward stops found along highway segment corridor.")
                    break
                
                leg_distance = min((total_distance - current_dist_milestone), max_range * 0.9)
                optimal_stop, fuel_cost, reason = self.find_optimal_stop(stops_in_range, leg_distance)
                
                if not optimal_stop:
                    break
                
                if optimal_stop['absolute_distance_from_start'] <= current_dist_milestone:
                    print("       ⚠️  Stuck protection: Selected stop does not advance forward.")
                    break
                
                print(f"       ✅ {optimal_stop['name']} - ${fuel_cost:.2f} ({reason})")
                
                fuel_stops.append({
                    'stop_number': stop_number,
                    'stop': optimal_stop,
                    'distance_from_start': round(optimal_stop['absolute_distance_from_start'], 1),
                    'distance_to_next': round(total_distance - optimal_stop['absolute_distance_from_start'], 1),
                    'distance_traveled': round(optimal_stop['distance_from_current'], 1),
                    'fuel_cost_here': round(fuel_cost, 2),
                    'selection_reason': reason
                })
                
                current_dist_milestone = optimal_stop['absolute_distance_from_start']
                stop_number += 1
            
            last_stop_price = fuel_stops[-1]['stop']['price_per_gallon'] if fuel_stops else 3.50
            remaining_miles = total_distance - current_dist_milestone
            final_leg_cost = (remaining_miles / self.vehicle.mpg) * last_stop_price
            total_fuel_cost = sum(s['fuel_cost_here'] for s in fuel_stops) + final_leg_cost
            
            return {
                'total_distance': round(total_distance, 1),
                'total_fuel_cost': round(total_fuel_cost, 2),
                'cost_per_mile': round(total_fuel_cost / total_distance, 4) if total_distance > 0 else 0,
                'start_location': start_location,
                'end_location': end_location,
                'start_lat': start_coords[0],
                'start_lng': start_coords[1],
                'end_lat': end_coords[0],
                'end_lng': end_coords[1],
                'route_coordinates': route_coords, 
                'fuel_stops': fuel_stops,
                'states_traversed': sorted(list(states_to_geocode)),
                'no_stops_needed': len(fuel_stops) == 0 and (total_distance <= self.vehicle.available_tank_range)
            }
        except Exception as e:
            print(f"\n❌ Optimization error: {str(e)}")
            raise