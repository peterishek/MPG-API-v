import csv
from django.core.management.base import BaseCommand
from api.models import FuelStop


class Command(BaseCommand):
    help = 'Load fuel prices from CSV file into database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing fuel prices'
        )
    
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                created_count = 0
                updated_count = 0
                error_count = 0
                
                for row in reader:
                    try:
                        # Skip if coordinates are missing (we need them for distance calculation)
                        if not row.get('City') or not row.get('State'):
                            continue
                        
                        # For CSV without explicit coordinates, we'll add them via geocoding
                        # This is a placeholder - in production, you'd geocode these
                        opis_id = row['OPIS Truckstop ID']
                        
                        fuel_stop, created = FuelStop.objects.update_or_create(
                            opis_id=opis_id,
                            defaults={
                                'name': row['Truckstop Name'].strip(),
                                'address': row['Address'].strip(),
                                'city': row['City'].strip(),
                                'state': row['State'].strip(),
                                'price_per_gallon': float(row['Retail Price']),
                                'latitude': 0.0,  # Placeholder - needs geocoding
                                'longitude': 0.0,  # Placeholder - needs geocoding
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                        
                        if (created_count + updated_count) % 100 == 0:
                            self.stdout.write(
                                f'Processed {created_count + updated_count} records...'
                            )
                    
                    except (ValueError, KeyError) as e:
                        error_count += 1
                        self.stderr.write(f'Error processing row: {str(e)}')
                        continue
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSuccessfully loaded {created_count} new records '
                        f'and updated {updated_count} existing records. '
                        f'({error_count} errors)'
                    )
                )
        
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {csv_file}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
