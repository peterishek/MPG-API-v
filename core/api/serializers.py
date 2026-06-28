from rest_framework import serializers
from .models import Vehicle, FuelStop, Route, RouteFuelStop, OptimizedRoute, OptimizedRouteStop


class VehicleSerializer(serializers.ModelSerializer):
    """Serialize Vehicle model"""
    class Meta:
        model = Vehicle
        fields = ['id', 'name', 'range_max', 'available_tank_range', 'mpg']


class FuelStopSerializer(serializers.ModelSerializer):
    """Serialize FuelStop model"""
    class Meta:
        model = FuelStop
        fields = ['id', 'opis_id', 'name', 'city', 'state', 'latitude', 'longitude', 'price_per_gallon']


class RouteFuelStopSerializer(serializers.ModelSerializer):
    """Serialize generic fuel stops on a route"""
    fuel_stop = FuelStopSerializer(read_only=True)
    
    class Meta:
        model = RouteFuelStop
        fields = ['id', 'stop_order', 'fuel_stop', 'distance_from_start']


class OptimizedRouteStopSerializer(serializers.ModelSerializer):
    """Serialize optimization-specific fuel stops with costs"""
    fuel_stop = FuelStopSerializer(read_only=True)
    
    class Meta:
        model = OptimizedRouteStop
        fields = [
            'id', 'stop_order', 'fuel_stop', 'distance_from_start',
            'distance_to_destination', 'distance_traveled', 'fuel_cost_here',
            'selection_reason'
        ]


class RouteSerializer(serializers.ModelSerializer):
    """Serialize base Route model"""
    fuel_stops = RouteFuelStopSerializer(many=True, read_only=True)
    
    class Meta:
        model = Route
        fields = [
            'id', 'start_location', 'end_location',
            'start_lat', 'start_lng', 'end_lat', 'end_lng',
            'total_distance', 'route_coordinates', 'fuel_stops', 'created_at'
        ]


class OptimizedRouteSerializer(serializers.ModelSerializer):
    """Serialize OptimizedRoute with vehicle and optimization stops"""
    vehicle = VehicleSerializer(read_only=True)
    # fuel_stops = RouteFuelStopSerializer(many=True, read_only=True)
    fuel_stops_optimized = OptimizedRouteStopSerializer(many=True, read_only=True)
    
    class Meta:
        model = OptimizedRoute
        fields = [
            'id', 'vehicle', 'start_location', 'end_location',
            'start_lat', 'start_lng', 'end_lat', 'end_lng',
            'total_distance', 'total_fuel_cost', 'route_coordinates',

            # 'fuel_stops',
            'fuel_stops_optimized', 'created_at'
        ]


class OptimizeRouteRequestSerializer(serializers.Serializer):
    """Validate incoming optimize route request"""
    start_location = serializers.CharField(max_length=255)
    end_location = serializers.CharField(max_length=255)
    vehicle_id = serializers.IntegerField()
    
    def validate_vehicle_id(self, value):
        if value <= 0:
            raise serializers.ValidationError("Vehicle ID must be positive")
        return value
    
    def validate_start_location(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Start location cannot be empty")
        return value.strip()
    
    def validate_end_location(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("End location cannot be empty")
        return value.strip()