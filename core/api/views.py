from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from .models import Vehicle, Route, RouteFuelStop, OptimizedRoute, OptimizedRouteStop, FuelStop
from .serializers import (
    VehicleSerializer, OptimizedRouteSerializer,
    OptimizeRouteRequestSerializer
)
from .optimizer import Optimizer


# ==================== MAP VIEW ====================

def map_view(request):
    """Serve the HTML map interface"""
    return render(request, 'index.html')


# ==================== VEHICLE ENDPOINTS ====================


@api_view(["POST"])
def create_vehicle(request):
    """
    POST /api/vehicles/

    Request body:
    {
        "name": "Tesla Model 3",
        "available_tank_range": 500,
        "range_max": 500,
        "mpg": 10
    }
    """
    serializer = VehicleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def list_vehicles(request):
    """
    GET: List all vehicles
    POST: Create a new vehicle
    """
    if request.method == 'GET':
        vehicles = Vehicle.objects.all()
        serializer = VehicleSerializer(vehicles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = VehicleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==================== ROUTE OPTIMIZATION ====================

@api_view(['POST'])
def optimize_route(request):
    """
    Optimize a route for fuel stops and calculate total fuel cost
    
    Request body:
    {
        "start_location": "Phoenix, AZ",
        "end_location": "Los Angeles, CA",
        "vehicle_id": 1
    }
    """
    try:
        # Validate incoming request
        serializer = OptimizeRouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_location = serializer.validated_data['start_location']
        end_location = serializer.validated_data['end_location']
        vehicle_id = serializer.validated_data['vehicle_id']
        
        # Get vehicle
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            return Response(
                {'error': f'Vehicle with id {vehicle_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        print(f"\n📍 Starting optimization with {vehicle.name}")
        
        # Run optimization algorithm
        optimizer = Optimizer(vehicle)
        optimization_result = optimizer.optimize_route(start_location, end_location)
        
        # Create Route (base record)
        route = Route.objects.create(
            start_location=optimization_result['start_location'],
            end_location=optimization_result['end_location'],
            start_lat=optimization_result['start_lat'],
            start_lng=optimization_result['start_lng'],
            end_lat=optimization_result['end_lat'],
            end_lng=optimization_result['end_lng'],
            total_distance=optimization_result['total_distance'],
            route_coordinates=optimization_result['route_coordinates']
        )
        
        print(f"✅ Created Route ID: {route.id}")
        
        # # Create RouteFuelStop records (generic stops)
        # for i, stop_info in enumerate(optimization_result['fuel_stops'], 1):
        #     fuel_stop = FuelStop.objects.get(id=stop_info['stop']['id'])
            
        #     RouteFuelStop.objects.create(
        #         route=route,
        #         fuel_stop=fuel_stop,
        #         stop_order=i,
        #         distance_from_start=stop_info['distance_from_start']
        #     )
        
        print(f"✅ Created {len(optimization_result['fuel_stops'])} RouteFuelStop records")
        
        # Create OptimizedRoute (inherits Route data)
        optimized_route = OptimizedRoute.objects.create(
            # Inherited from Route
            start_location=optimization_result['start_location'],
            end_location=optimization_result['end_location'],
            start_lat=optimization_result['start_lat'],
            start_lng=optimization_result['start_lng'],
            end_lat=optimization_result['end_lat'],
            end_lng=optimization_result['end_lng'],
            total_distance=optimization_result['total_distance'],
            route_coordinates=optimization_result['route_coordinates'],
            # Optimization specific
            vehicle=vehicle,
            total_fuel_cost=optimization_result['total_fuel_cost']
        )
        
        print(f"✅ Created OptimizedRoute ID: {optimized_route.id}")
        
        # Create OptimizedRouteStop records (optimization specific)
        for i, stop_info in enumerate(optimization_result['fuel_stops'], 1):
            fuel_stop = FuelStop.objects.get(id=stop_info['stop']['id'])
            
            # Calculate distance_traveled for this leg
            if i == 1:
                distance_traveled = stop_info['distance_from_start']
            else:
                distance_traveled = vehicle.available_tank_range  # ✅ USE VEHICLE RANGE
            
            OptimizedRouteStop.objects.create(
                optimized_route=optimized_route,
                fuel_stop=fuel_stop,
                stop_order=i,
                distance_from_start=stop_info['distance_from_start'],
                distance_to_destination=stop_info['distance_to_next'],
                distance_traveled=distance_traveled,
                fuel_cost_here=stop_info['fuel_cost_here'],
                selection_reason=stop_info['selection_reason']
            )
            
            print(f"    ✅ Stop {i}: {fuel_stop.name} (${stop_info['fuel_cost_here']:.2f})")
        
        print(f"✅ Created {len(optimization_result['fuel_stops'])} OptimizedRouteStop records")
        
        # Serialize and return
        response_serializer = OptimizedRouteSerializer(optimized_route)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        print(f"❌ Optimization error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': f'Route optimization failed: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


# ==================== ROUTE RETRIEVAL ====================

@api_view(['GET'])
def list_routes(request):
    """Get all optimized routes"""
    optimized_routes = OptimizedRoute.objects.all().prefetch_related(
        'fuel_stops', 'fuel_stops_optimized'
    ).order_by('-created_at')
    serializer = OptimizedRouteSerializer(optimized_routes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_route(request, route_id):
    """Get a specific optimized route with its fuel stops"""
    try:
        optimized_route = OptimizedRoute.objects.prefetch_related(
            'fuel_stops', 'fuel_stops_optimized'
        ).get(id=route_id)
        serializer = OptimizedRouteSerializer(optimized_route)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except OptimizedRoute.DoesNotExist:
        return Response(
            {'error': f'Route with id {route_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def get_route_fuel_stops(request, route_id):
    """Get all fuel stops for a specific optimized route"""
    try:
        optimized_route = OptimizedRoute.objects.prefetch_related(
            'fuel_stops_optimized'
        ).get(id=route_id)
        
        fuel_stops = optimized_route.get_fuel_stops_optimized()
        
        data = {
            'route_id': route_id,
            'route': f"{optimized_route.start_location} → {optimized_route.end_location}",
            'vehicle': str(optimized_route.vehicle),
            'total_distance': optimized_route.total_distance,
            'total_fuel_cost': optimized_route.total_fuel_cost,
            'stops': [
                {
                    'order': stop.stop_order,
                    'name': stop.fuel_stop.name,
                    'city': stop.fuel_stop.city,
                    'state': stop.fuel_stop.state,
                    'price_per_gallon': stop.fuel_stop.price_per_gallon,
                    'distance_from_start': stop.distance_from_start,
                    'distance_to_destination': stop.distance_to_destination,
                    'distance_traveled': stop.distance_traveled,
                    'fuel_cost_here': stop.fuel_cost_here,
                    'selection_reason': stop.selection_reason
                }
                for stop in fuel_stops
            ]
        }
        
        return Response(data, status=status.HTTP_200_OK)
    except OptimizedRoute.DoesNotExist:
        return Response(
            {'error': f'Route with id {route_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )


# ==================== STATISTICS ====================

@api_view(['GET'])
def route_statistics(request):
    """Get statistics about all routes"""
    routes = OptimizedRoute.objects.all()
    
    if not routes.exists():
        return Response(
            {'error': 'No routes found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    total_routes = routes.count()
    total_distance = sum(r.total_distance for r in routes)
    total_cost = sum(r.total_fuel_cost for r in routes)
    avg_cost_per_mile = total_cost / total_distance if total_distance > 0 else 0
    
    data = {
        'total_routes': total_routes,
        'total_distance_miles': round(total_distance, 2),
        'total_fuel_cost': round(total_cost, 2),
        'average_cost_per_mile': round(avg_cost_per_mile, 3),
        'cost_per_route': round(total_cost / total_routes, 2) if total_routes > 0 else 0
    }
    
    return Response(data, status=status.HTTP_200_OK)
