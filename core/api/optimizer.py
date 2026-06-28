
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
        
        # FIX: Base cost on actual distance traveled to station, not artificial leg boundary limit
        fuel_cost = (optimal_stop['distance_from_current'] / self.vehicle.mpg) * optimal_stop['price_per_gallon']
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