import os
import glob
from datetime import datetime

def parse_nmea_coordinate(coord_str, direction):
    if not coord_str or not direction:
        return None
    try:
        coord_float = float(coord_str)
        degrees = int(coord_float / 100)
        minutes = coord_float - (degrees * 100)
        decimal = degrees + (minutes / 60)
        if direction in ['S', 'W']:
            decimal = -decimal
        return decimal
    except:
        return None

def parse_gprmc(line):
    parts = line.strip().split(',')
    if len(parts) < 10 or parts[2] != 'A':
        return None
    
    time_str = parts[1]
    lat_str = parts[3]
    lat_dir = parts[4]
    lon_str = parts[5]
    lon_dir = parts[6]
    speed_knots = parts[7]
    course = parts[8]
    date_str = parts[9]
    
    if not all([time_str, lat_str, lat_dir, lon_str, lon_dir, date_str]):
        return None
    
    lat = parse_nmea_coordinate(lat_str, lat_dir)
    lon = parse_nmea_coordinate(lon_str, lon_dir)
    
    if lat is None or lon is None:
        return None
    
    try:
        speed = float(speed_knots) if speed_knots else 0.0
    except:
        speed = 0.0
    
    try:
        heading = float(course) if course else 0.0
    except:
        heading = 0.0
    
    try:
        dt = datetime.strptime(date_str + time_str.split('.')[0], '%d%m%y%H%M%S')
    except:
        dt = None
    
    return {
        'lat': lat,
        'lon': lon,
        'speed': speed,
        'heading': heading,
        'datetime': dt
    }

def parse_gpgga(line):
    parts = line.strip().split(',')
    if len(parts) < 10:
        return None
    
    time_str = parts[1]
    lat_str = parts[2]
    lat_dir = parts[3]
    lon_str = parts[4]
    lon_dir = parts[5]
    
    if not all([lat_str, lat_dir, lon_str, lon_dir]):
        return None
    
    lat = parse_nmea_coordinate(lat_str, lat_dir)
    lon = parse_nmea_coordinate(lon_str, lon_dir)
    
    if lat is None or lon is None:
        return None
    
    return {
        'lat': lat,
        'lon': lon
    }

def read_gps_file(filename):
    points = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith('$GP'):
                continue
            
            if line.startswith('$GPRMC'):
                data = parse_gprmc(line)
                if data:
                    points.append(data)
            elif line.startswith('$GPGGA'):
                data = parse_gpgga(line)
    
    return points

def generate_kml(points, output_filename):
    if not points:
        print("No points to generate KML")
        return
    
    print(f"First point: lat={points[0]['lat']}, lon={points[0]['lon']}")
    print(f"Last point: lat={points[-1]['lat']}, lon={points[-1]['lon']}")
    
    kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>GPS Track</name>
<Placemark>
<name>Route</name>
<LineString>
<tessellate>1</tessellate>
<coordinates>
'''
    
    kml_coords = ''
    for point in points:
        kml_coords += f"{point['lon']:.7f},{point['lat']:.7f},3\n"
    
    kml_footer = '''</coordinates>
</LineString>
</Placemark>
</Document>
</kml>'''
    
    with open(output_filename, 'w') as f:
        f.write(kml_header)
        f.write(kml_coords)
        f.write(kml_footer)

def process_gps_file(input_file):
    print(f"Processing {input_file}...")
    
    points = read_gps_file(input_file)
    print(f"Read {len(points)} points")
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{base_name}.kml"
    generate_kml(points, output_file)
    print(f"Generated {output_file}")
    print()

def main():
    gps_files = glob.glob("Some_Example_GPS_Files/*.txt")
    
    if not gps_files:
        print("No GPS files found in Some_Example_GPS_Files/")
        return
    
    for gps_file in gps_files:
        process_gps_file(gps_file)

if __name__ == "__main__":
    main()