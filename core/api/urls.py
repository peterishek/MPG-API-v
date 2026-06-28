
from django.urls import path
from . import views


urlpatterns = [
    # Route optimization
    path('optimize-route/', views.optimize_route, name='optimize-route'),
    path('routes/', views.list_routes, name='list-routes'),
    path('routes/<int:route_id>/', views.get_route, name='get-route'),
    path('routes/<int:route_id>/fuel-stops/', views.get_route_fuel_stops, name='get_route_fuel_stops'),
    path('statistics/', views.route_statistics, name='route_statistics'),
    
    # Vehicle management
    path('vehicles/', views.list_vehicles, name='list-vehicles'),
    path('vehicles/create/', views.create_vehicle, name='create-vehicle'),

    # Map view
    path('map/', views.map_view, name='map-view'),
]
