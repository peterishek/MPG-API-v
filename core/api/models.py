from django.db import models


class Vehicle(models.Model):
    """Vehicle specifications for route optimization"""
    name = models.CharField(max_length=100, unique=True)
    range_max = models.IntegerField(default=500, help_text="Max range on a full tank (miles)")
    available_tank_range = models.IntegerField(default=500, help_text="Currently available tank range (miles)")
    mpg = models.IntegerField(default=10, help_text="Miles per gallon")
    
    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} (Available: {self.available_tank_range}mi, Max: {self.range_max}mi, {self.mpg} MPG)"


class FuelStop(models.Model):
    """Fuel stop location with pricing information"""
    opis_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=2, db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    price_per_gallon = models.FloatField(help_text="Price in USD")
    
    class Meta:
        verbose_name = "Fuel Stop"
        verbose_name_plural = "Fuel Stops"
        indexes = [
            models.Index(fields=['city', 'state']),
            models.Index(fields=['price_per_gallon']),
            models.Index(fields=['latitude', 'longitude']),
        ]
        ordering = ['state', 'city', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} (${self.price_per_gallon:.3f})"
    
    def to_dict(self):
        """Convert to dictionary for algorithm lookups"""
        return {
            'id': self.id,
            'opis_id': self.opis_id,
            'name': self.name,
            'city': self.city,
            'state': self.state,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'price_per_gallon': self.price_per_gallon
        }


class Route(models.Model):
    """
    Base route with location, path, and fuel stops information.
    Can be used for any route (optimized or not).
    """
    start_location = models.CharField(max_length=255, help_text="Start location (e.g., Phoenix, AZ)")
    end_location = models.CharField(max_length=255, help_text="End location (e.g., Los Angeles, CA)")
    start_lat = models.FloatField()
    start_lng = models.FloatField()
    end_lat = models.FloatField()
    end_lng = models.FloatField()
    total_distance = models.FloatField(help_text="Total route distance in miles")
    route_coordinates = models.JSONField(help_text="GeoJSON coordinates of the route")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Route"
        verbose_name_plural = "Routes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.start_location} → {self.end_location} ({self.total_distance:.1f}mi)"
    
    def get_fuel_stops(self):
        """Get all fuel stops on this route in order"""
        return self.fuel_stops.all().order_by('stop_order')


class RouteFuelStop(models.Model):
    """
    Generic fuel stops along a route.
    Links Route to FuelStop with basic information.
    """
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name='fuel_stops'
    )
    fuel_stop = models.ForeignKey(
        FuelStop,
        on_delete=models.PROTECT,
        related_name='routes_with_this_stop'
    )
    stop_order = models.PositiveIntegerField(help_text="Order of this stop in the route")
    distance_from_start = models.FloatField(help_text="Distance from route start to this stop (miles)")
    
    class Meta:
        verbose_name = "Route Fuel Stop"
        verbose_name_plural = "Route Fuel Stops"
        ordering = ['route', 'stop_order']
        unique_together = ('route', 'stop_order')
    
    def __str__(self):
        return f"Stop {self.stop_order}: {self.fuel_stop.name}"


class OptimizedRoute(Route):
    """
    Optimized route with fuel stops and cost calculations.
    Inherits from Route and adds optimization-specific data.
    """
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='optimized_routes')
    total_fuel_cost = models.FloatField(help_text="Total estimated fuel cost in USD")
    
    class Meta:
        verbose_name = "Optimized Route"
        verbose_name_plural = "Optimized Routes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.vehicle.name}] {self.start_location} → {self.end_location} (${self.total_fuel_cost:.2f})"
    
    def get_fuel_stops_optimized(self):
        """Get all optimized fuel stops (with costs and reasons)"""
        return self.fuel_stops_optimized.all().order_by('stop_order')
    
    def recalculate_total_cost(self):
        """Recalculate total fuel cost from individual stops"""
        total = sum(stop.fuel_cost_here for stop in self.get_fuel_stops_optimized())
        self.total_fuel_cost = total
        self.save()
        return total


class OptimizedRouteStop(models.Model):
    """
    Optimization-specific fuel stop with cost calculations and selection reasoning.
    Extends the concept of RouteFuelStop with optimization details.
    """
    optimized_route = models.ForeignKey(
        OptimizedRoute,
        on_delete=models.CASCADE,
        related_name='fuel_stops_optimized'
    )
    fuel_stop = models.ForeignKey(
        FuelStop,
        on_delete=models.PROTECT,
        related_name='optimized_route_stops'
    )
    stop_order = models.PositiveIntegerField(help_text="Order of this stop in the route")
    distance_from_start = models.FloatField(help_text="Distance from route start to this stop (miles)")
    distance_to_destination = models.FloatField(help_text="Distance from this stop to final destination (miles)")
    distance_traveled = models.FloatField(help_text="Distance traveled since last stop (miles)")
    fuel_cost_here = models.FloatField(help_text="Fuel cost for next leg: (distance_traveled / mpg) * price_per_gallon")
    selection_reason = models.TextField(help_text="Why this stop was selected (closest/cheapest/reachable)")
    
    class Meta:
        verbose_name = "Optimized Route Stop"
        verbose_name_plural = "Optimized Route Stops"
        ordering = ['optimized_route', 'stop_order']
        unique_together = ('optimized_route', 'stop_order')
    
    def __str__(self):
        return f"Stop {self.stop_order}: {self.fuel_stop.name} (${self.fuel_cost_here:.2f})"
    
    def calculate_fuel_cost(self):
        """
        Calculate fuel cost based on distance and vehicle specs.
        Formula: (distance_traveled / mpg) * price_per_gallon
        """
        mpg = self.optimized_route.vehicle.mpg
        price = self.fuel_stop.price_per_gallon
        cost = (self.distance_traveled / mpg) * price
        return cost
    
    def save(self, *args, **kwargs):
        """Auto-calculate fuel cost before saving"""
        if self.distance_traveled and not self.fuel_cost_here:
            self.fuel_cost_here = self.calculate_fuel_cost()
        super().save(*args, **kwargs)