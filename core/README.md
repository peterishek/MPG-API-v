# 🚗 MPG API V Fuel Optimizer - Route & Cost Optimization System

A Django REST API that optimizes truck routes by calculating the most cost-effective fuel stops based on distance, vehicle capacity, and real-time fuel prices.

## 📋 Table of Contents

* Overview
* Features
* Technology Stack
* Data Structures & Algorithms
* System Architecture
* Installation
* API Endpoints
* Testing Guide
* Examples

## 🎯 Overview

**Fuel Optimizer** solves the **Vehicle Routing with Fuel Stop Optimization Problem** - a variation of the Traveling Salesman Problem (TSP) with constraints.

### The Problem

* A truck needs to travel from point A to point B.
* The truck has a limited fuel tank range (e.g., 500 miles).
* 8,000+ fuel stops across the USA with varying prices.
* **Goal**: Find the route with the **lowest total fuel cost**.

### The Solution

1. **Lazy Geocoding**: Only geocode fuel stops along the actual route path states.
2. **Optimal Stop Selection**: Use intelligent decision logic to pick best stops.
3. **Cost Calculation**: (distance_traveled / mpg) × price_per_gallon
4. **Multi-State Support**: Detect and geocode all states on the route path.

## ✨ Features

### Core Optimization

* ✅ OSRM routing (Open Route Service Matrix)
* ✅ Lazy geocoding (only geocode route-specific fuel stops)
* ✅ Multi-state detection (intermediate states on route via reverse lookup sampling)
* ✅ Intelligent forward-progress stop selection (closest/cheapest/reachable)
* ✅ Infinite loop stuck protection and real-time geocoding terminal streaming

### Data Management

* ✅ 8,000+ fuel stops database (loaded from historical industrial CSV data)
* ✅ Vehicle profiles (split range thresholds: maximum capacity vs. initial available range)
* ✅ Complete route history and configuration state persistence
* ✅ Optimization audit trail with clear logic breakdown strings

## 🛠️ Technology Stack

| Layer               | Technology                         | Purpose                                             |
| ------------------- | ---------------------------------- | --------------------------------------------------- |
| **Backend**   | Django 4.x / Django REST Framework | Core REST API framework and data models             |
| **Database**  | PostgreSQL                         | Fuel stops spatial mapping, routes, and vehicles    |
| **Routing**   | OSRM                               | Highway polyline calculation & step coordinates     |
| **Geocoding** | Nominatim API                      | Location text ⇄ coordinate bound conversion        |
| **Frontend**  | HTML5 + Leaflet.js                 | Interactive vector mapping and path trace rendering |

## 📊 Data Structures & Algorithms

### Data Structures

#### 1. **FuelStop (Hash Map Lookup)**

```json
{
  "id": 123,
  "opis_id": "ABC-456",
  "name": "Pilot Flying J",
  "city": "Blythe",
  "state": "CA",
  "latitude": 33.6156,
  "longitude": -114.5880,
  "price_per_gallon": 3.45
}
```

* **DSA Application**: Database index conversion to in-memory Python dictionaries for fast lookups.

#### 2. **Route (Graph Path Polyline)**

```
start_coordinates → [[lat1, lng1], [lat2, lng2], ...] → end_coordinates
```

* **DSA Application**: Sequential linear array of coordinate pairs representing the OSRM travel corridor layout.

#### 3. **OptimizedRouteStop (Ordered List)**

```
Stop 1: Holbrook, AZ  → 186.5 mi absolute step → $144.85 leg cost
Stop 2: Lupton, AZ    → 259.0 mi absolute step → $148.45 leg cost
```

* **DSA Application**: Relational order tracking using foreign keys paired with explicit incremental counters.

### Algorithms

#### 1. **Lazy Geocoding Algorithm**

```
Input: start_location, end_location, route_coordinates
Output: Geocoded fuel stops in route states

Step 1: Extract states from start/end locations text strings.
Step 2: Extract intermediate states along the OSRM route path.
        → Sample up to 15 coordinate intervals along the polyline.
        → Reverse-geocode samples to pull unique 2-letter state codes.
Step 3: Geocode only missing database records matching these specific states.
        → Loop through targets and request bounds from the Nominatim API.
        → Stream real-time progress steps explicitly to the console.
```

#### 2. **Optimal Fuel Stop Selection (Decision Tree)**

```
Input: stops_in_range, leg_distance
Output: optimal_stop, fuel_cost, selection_reason

IF closest_stop == cheapest_stop:
    RETURN closest_stop ("Same location (closest and cheapest)")

ELSE:
    remaining_from_closest = leg_distance - closest_stop.distance_from_current
    remaining_from_cheapest = leg_distance - cheapest_stop.distance_from_current

    closest_reachable = remaining_from_closest <= vehicle.available_tank_range
    cheapest_reachable = remaining_from_cheapest <= vehicle.available_tank_range

    IF closest_reachable AND cheapest_reachable:
        RETURN cheapest_stop ("Cheapest option (both reachable)")
    ELIF closest_reachable:
        RETURN closest_stop ("Closest is only reachable option")
    ELSE:
        RETURN cheapest_stop ("Default to cheapest")
```

#### 3. **Haversine Distance Calculation**

Calculates the great-circle distance between two points on a sphere given their longitudes and latitudes. Used to extract candidates within a 3-mile corridor radius of the OSRM path polyline.
Where R = 3959 \text{ miles} (Earth's radius).

#### 4. **Greedy Route Optimization (Milestone-Corridor Engine)**

```
Input: route_coordinates, cumulative_distances, total_distance, vehicle
Output: [Stop 1, Stop 2, ..., Stop N] (ordered list of selected stations)

current_dist_milestone = 0
stop_number = 1
stops = []

WHILE (total_distance - current_dist_milestone) > vehicle.available_tank_range * 0.85:
  
    // Determine look-ahead window size based on fuel capacity state
    IF stop_number == 1:
        search_window = vehicle.available_tank_range
    ELSE:
        search_window = vehicle.tank_range_max * 0.85
      
    // Find candidate stations matching the active state path corridor
    candidates = find_stops_along_corridor(current_dist_milestone, search_window)
  
    IF NOT candidates:
        BREAK // No forward stations found along highway segment
      
    leg_distance = min((total_distance - current_dist_milestone), vehicle.tank_range_max * 0.9)
    optimal_stop, fuel_cost, reason = select_optimal_stop(candidates, leg_distance)
  
    // STUCK PROTECTION GUARDRAIL: Verify strict forward motion down the polyline
    IF optimal_stop.absolute_distance_from_start <= current_dist_milestone:
        BREAK // Force termination to prevent infinite structural loop
      
    stops.append(optimal_stop)
  
    // Update active journey tracking state forward
    current_dist_milestone = optimal_stop.absolute_distance_from_start
    stop_number += 1

RETURN stops
```

> **Why Greedy?** > The Fuel Stop Routing Problem over long distances is highly combinatorial (NP-hard). This greedy approach tracks absolute highway progression down a vector grid, making optimal cost evaluations point-by-point. It drops computational complexity down to O(N) for blistering execution speeds.

## 🏗️ System Architecture

### Model Hierarchy

```
Vehicle
├── name: "Mercedes-Benz C300"
├── available_tank_range: 500 mi  <-- Fuel left in current tank at start
├── tank_range_max: 500 mi        <-- Total capacity when filled 100%
└── mpg: 10

FuelStop (8,000+ source records loaded from CSV dataset)
├── name, city, state
├── latitude, longitude (0.0 default, populated via lazy geocoding)
└── price_per_gallon

Route (Base Layout Engine)
├── start_location, end_location
├── route_coordinates (Full polyline array)
└── total_distance

OptimizedRoute (Inherits Base Route Schema)
├── vehicle (Foreign Key)
├── total_fuel_cost
└── fuel_stops_optimized → Ordered mapping with individual leg costs
```

## 📦 Installation & Setup

### 1. Prerequisites

* Python 3.10+
* PostgreSQL 14+
* Internet connection (for initial live routing and Nominatim geocoding)

### 2. Environment Configuration

Create an .env file in your root backend package directory to handle service bindings smoothly:

```env
DEBUG=True
SECRET_KEY=your-django-custom-secret-key-string
DB_NAME=mpg_optimizer
DB_USER=postgres
DB_PASSWORD=yoursecurepassword
DB_HOST=localhost
DB_PORT=5432
```

### 3. Execution Commands

```bash
# Clone and navigate into directory
cd api

# Install requirements
pip install -r requirements.txt

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Seed data records from CSV asset source
python manage.py load_fuel_stops fuel-prices.csv

# Configure initial vehicle model via python shell
python manage.py shell
```

```python
from api.models import Vehicle
Vehicle.objects.create(
    name="Mercedes-Benz C300",
    available_tank_range=500,
    tank_range_max=500,
    mpg=10
)
exit()
```

```bash
# Start your local server instance
python manage.py runserver
```

## 🔌 API Endpoints

### 🚙 Vehicle Profiles

* GET  /api/vehicles/ — Returns list profiles.
* POST /api/vehicles/ — Registers a new configuration payload.

### 🗺️ Route Optimization Engine

* POST /api/optimize-route/ — Submits engine calculations.
  **Request Payload JSON**:

```json
{
  "start_location": "Phoenix, AZ",
  "end_location": "New York, NY",
  "vehicle_id": 1
}
```

## 🧪 Testing Guide

Run the suite to evaluate spatial constraints, lazy loop updates, and route calculations:

```bash
# Run all unit tests
python manage.py test api.tests

# Target optimization integration module directly
python manage.py test api.tests.test_optimization
```

## 📈 Performance Benchmarks

| Phase / Operation                  | Execution Velocity          | Processing Strategy                                    |
| ---------------------------------- | --------------------------- | ------------------------------------------------------ |
| **OSRM Corridors Fetch**     | < 400 \text{ ms}            | Non-blocking synchronous HTTP matrix array stream      |
| **Lazy Geocoding Iteration** | \sim 1.2 \text{ sec / city} | Nominatim compliance throttling with live log feedback |
| **Greedy Decision Loop**     | < 50 \text{ ms}             | Vector math indexing using local memory bounds         |
