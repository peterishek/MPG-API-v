from django.contrib import admin
from django.utils.html import format_html
from .models import Vehicle, FuelStop, Route, RouteFuelStop, OptimizedRoute, OptimizedRouteStop


# ==================== VEHICLE ADMIN ====================

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """Admin interface for Vehicle model"""
    list_display = ['name', 'range_max', 'available_tank_range', 'mpg', 'optimized_routes_count']
    list_filter = ['range_max', 'available_tank_range', 'mpg']
    search_fields = ['name']
    readonly_fields = ['created_info']
    
    fieldsets = (
        ('Vehicle Information', {
            'fields': ('name', 'range_max', 'available_tank_range', 'mpg')
        }),
        ('System Info', {
            'fields': ('created_info',),
            'classes': ('collapse',)
        }),
    )
    
    def optimized_routes_count(self, obj):
        """Show count of optimized routes for this vehicle"""
        count = obj.optimized_routes.count()
        return format_html(
            '<span style="background-color: #dff0d8; padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    optimized_routes_count.short_description = 'Routes Optimized'
    
    def created_info(self, obj):
        """Display creation info"""
        return "Auto-managed"
    created_info.short_description = "Created"


# ==================== FUEL STOP ADMIN ====================

@admin.register(FuelStop)
class FuelStopAdmin(admin.ModelAdmin):
    """Admin interface for FuelStop model"""
    list_display = ['name', 'city_state', 'price_per_gallon', 'coordinates', 'status']
    list_filter = ['state', 'price_per_gallon', 'city']
    search_fields = ['name', 'city', 'state', 'opis_id']
    readonly_fields = ['opis_id', 'id']
    
    fieldsets = (
        ('Stop Information', {
            'fields': ('id', 'opis_id', 'name', 'city', 'state')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'coordinates_map')
        }),
        ('Pricing', {
            'fields': ('price_per_gallon',)
        }),
    )
    
    def city_state(self, obj):
        """Display city and state together"""
        return f"{obj.city}, {obj.state}"
    city_state.short_description = 'Location'
    
    def coordinates(self, obj):
        """Display coordinates"""
        if obj.latitude == 0.0 or obj.longitude == 0.0:
            return format_html('<span style="color: red;">Not geocoded</span>')
        return f"({obj.latitude:.4f}, {obj.longitude:.4f})"
    coordinates.short_description = 'Coordinates'
    
    def coordinates_map(self, obj):
        """Link to Google Maps"""
        if obj.latitude == 0.0 or obj.longitude == 0.0:
            return "Not geocoded yet"
        return format_html(
            '<a href="https://maps.google.com/?q={},{}" target="_blank">View on Google Maps</a>',
            obj.latitude, obj.longitude
        )
    coordinates_map.short_description = 'Map'
    
    def status(self, obj):
        """Show geocoding status"""
        if obj.latitude == 0.0 or obj.longitude == 0.0:
            return format_html('<span style="color: orange; font-weight: bold;">⚠️ Pending</span>')
        return format_html('<span style="color: green; font-weight: bold;">✅ Geocoded</span>')
    status.short_description = 'Status'


# ==================== ROUTE ADMIN ====================

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    """Admin interface for Route model"""
    list_display = ['route_display', 'total_distance', 'fuel_stops_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['start_location', 'end_location']
    readonly_fields = ['id', 'created_at', 'route_summary']
    
    fieldsets = (
        ('Route Endpoints', {
            'fields': ('id', 'start_location', 'end_location')
        }),
        ('Coordinates', {
            'fields': ('start_lat', 'start_lng', 'end_lat', 'end_lng')
        }),
        ('Route Data', {
            'fields': ('total_distance', 'route_coordinates', 'created_at')
        }),
        ('Summary', {
            'fields': ('route_summary',),
            'classes': ('collapse',)
        }),
    )
    
    def route_display(self, obj):
        """Display route in readable format"""
        return f"{obj.start_location} → {obj.end_location}"
    route_display.short_description = 'Route'
    
    def fuel_stops_count(self, obj):
        """Count fuel stops on this route"""
        count = obj.fuel_stops.count()
        return format_html(
            '<span style="background-color: #d9edf7; padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    fuel_stops_count.short_description = 'Stops'
    
    def route_summary(self, obj):
        """Display route summary"""
        stops = obj.fuel_stops.count()
        return f"Distance: {obj.total_distance:.1f}mi, Stops: {stops}"
    route_summary.short_description = 'Summary'


# ==================== ROUTE FUEL STOP ADMIN ====================

@admin.register(RouteFuelStop)
class RouteFuelStopAdmin(admin.ModelAdmin):
    """Admin interface for RouteFuelStop model"""
    list_display = ['get_route', 'stop_order', 'fuel_stop', 'distance_from_start']
    list_filter = ['route__start_location', 'fuel_stop__state']
    search_fields = ['route__start_location', 'fuel_stop__name']
    readonly_fields = ['route', 'fuel_stop', 'stop_order']
    
    fieldsets = (
        ('Route Information', {
            'fields': ('route', 'stop_order')
        }),
        ('Fuel Stop', {
            'fields': ('fuel_stop',)
        }),
        ('Distance', {
            'fields': ('distance_from_start',)
        }),
    )
    
    def get_route(self, obj):
        """Display route in readable format"""
        return f"{obj.route.start_location} → {obj.route.end_location}"
    get_route.short_description = 'Route'


# ==================== OPTIMIZED ROUTE ADMIN ====================

@admin.register(OptimizedRoute)
class OptimizedRouteAdmin(admin.ModelAdmin):
    """Admin interface for OptimizedRoute model"""
    list_display = ['route_display', 'vehicle', 'total_distance', 'total_fuel_cost', 'created_at']
    list_filter = ['vehicle', 'created_at']
    search_fields = ['start_location', 'end_location', 'vehicle__name']
    readonly_fields = ['id', 'created_at', 'route_stats', 'cost_per_mile']
    
    fieldsets = (
        ('Route Endpoints', {
            'fields': ('id', 'start_location', 'end_location')
        }),
        ('Coordinates', {
            'fields': ('start_lat', 'start_lng', 'end_lat', 'end_lng')
        }),
        ('Vehicle & Cost', {
            'fields': ('vehicle', 'total_fuel_cost', 'cost_per_mile')
        }),
        ('Route Data', {
            'fields': ('total_distance', 'route_coordinates', 'created_at')
        }),
        ('Statistics', {
            'fields': ('route_stats',),
            'classes': ('collapse',)
        }),
    )
    
    def route_display(self, obj):
        """Display route in readable format"""
        return f"{obj.start_location} → {obj.end_location}"
    route_display.short_description = 'Route'
    
    def cost_per_mile(self, obj):
        """Calculate and display cost per mile"""
        if obj.total_distance > 0:
            cpp = obj.total_fuel_cost / obj.total_distance
            return format_html(
                '<span style="color: #d9534f; font-weight: bold;">${:.3f}/mi</span>',
                cpp
            )
        return "N/A"
    cost_per_mile.short_description = 'Cost Per Mile'
    
    def route_stats(self, obj):
        """Display route statistics"""
        stops = obj.fuel_stops_optimized.count()
        cost_per_mile = obj.total_fuel_cost / obj.total_distance if obj.total_distance > 0 else 0
        return (
            f"Total Distance: {obj.total_distance:.1f} miles\n"
            f"Total Cost: ${obj.total_fuel_cost:.2f}\n"
            f"Cost/Mile: ${cost_per_mile:.3f}\n"
            f"Optimized Stops: {stops}"
        )
    route_stats.short_description = 'Statistics'


# ==================== OPTIMIZED ROUTE STOP ADMIN ====================

class OptimizedRouteStopInline(admin.TabularInline):
    """Inline admin for OptimizedRouteStop"""
    model = OptimizedRouteStop
    extra = 0
    readonly_fields = ['stop_order', 'distance_from_start', 'distance_to_destination', 'distance_traveled', 'fuel_cost_here']
    fields = ['stop_order', 'fuel_stop', 'distance_traveled', 'fuel_cost_here', 'selection_reason']
    can_delete = False


@admin.register(OptimizedRouteStop)
class OptimizedRouteStopAdmin(admin.ModelAdmin):
    """Admin interface for OptimizedRouteStop model"""
    list_display = ['get_route', 'stop_order', 'fuel_stop', 'distance_traveled', 'fuel_cost_here']
    list_filter = ['optimized_route__vehicle', 'selection_reason']
    search_fields = ['optimized_route__start_location', 'fuel_stop__name']
    readonly_fields = ['optimized_route', 'fuel_stop', 'stop_order', 'cost_calculation']
    
    fieldsets = (
        ('Route Information', {
            'fields': ('optimized_route', 'stop_order')
        }),
        ('Fuel Stop', {
            'fields': ('fuel_stop',)
        }),
        ('Distances', {
            'fields': ('distance_from_start', 'distance_to_destination', 'distance_traveled')
        }),
        ('Cost & Selection', {
            'fields': ('fuel_cost_here', 'selection_reason', 'cost_calculation')
        }),
    )
    
    def get_route(self, obj):
        """Display route in readable format"""
        return f"{obj.optimized_route.start_location} → {obj.optimized_route.end_location}"
    get_route.short_description = 'Route'
    
    def cost_calculation(self, obj):
        """Show cost calculation formula"""
        vehicle = obj.optimized_route.vehicle
        formula = (
            f"Formula: (distance_traveled / mpg) × price_per_gallon\n"
            f"= ({obj.distance_traveled:.1f}mi / {vehicle.mpg}mpg) × ${obj.fuel_stop.price_per_gallon:.3f}\n"
            f"= {obj.distance_traveled / vehicle.mpg:.2f}gal × ${obj.fuel_stop.price_per_gallon:.3f}\n"
            f"= ${obj.fuel_cost_here:.2f}"
        )
        return format_html('<pre style="font-family: monospace; font-size: 12px;">{}</pre>', formula)
    cost_calculation.short_description = 'Cost Calculation'


# ==================== ADMIN CUSTOMIZATION ====================

admin.site.site_header = "Fuel Optimizer Admin"
admin.site.site_title = "Fuel Optimizer"
admin.site.index_title = "Welcome to Fuel Optimizer Admin"