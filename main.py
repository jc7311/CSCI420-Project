# Jacky Chan and Ethan Chang
# CSCI 420 Project

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
        heading = float(course) if course else None
    except:
        heading = None
    
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

def normalize_angle(angle):
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle

def angle_difference(prev_heading, curr_heading):
    prev = normalize_angle(prev_heading)
    curr = normalize_angle(curr_heading)
    
    diff = curr - prev
    
    if diff < -180:
        diff += 360
    elif diff > 180:
        diff -= 360
    
    return diff

def detect_stops_and_turns(points):
    stops = []
    turns = []
    
    speed_threshold = 1.0
    min_speed_for_heading = 5.0
    turn_threshold = 25
    window_size = 10
    
    for i in range(len(points)):
        if points[i]['speed'] < speed_threshold:
            if i > 0 and points[i-1]['speed'] >= speed_threshold:
                stops.append(i)
    
    for i in range(window_size, len(points)):
        avg_speed = sum(p['speed'] for p in points[i-window_size:i+1]) / (window_size + 1)
        
        if avg_speed < min_speed_for_heading:
            continue
        
        start_idx = i - window_size
        
        if points[start_idx]['heading'] is None or points[i]['heading'] is None:
            continue
        
        moving_points = [p for p in points[start_idx:i+1] if p['speed'] > min_speed_for_heading and p['heading'] is not None]
        
        if len(moving_points) < 3:
            continue
        
        total_turn = angle_difference(moving_points[0]['heading'], moving_points[-1]['heading'])
        
        if total_turn < -turn_threshold:
            already_marked = False
            for t in turns:
                if abs(t - i) < window_size:
                    already_marked = True
                    break
            
            if not already_marked:
                turns.append(i)
    
    return stops, turns

def generate_kml(points, stops, turns, output_filename):
    if not points:
        print("No points to generate KML")
        return
    
    print(f"First point: lat={points[0]['lat']}, lon={points[0]['lon']}")
    print(f"Last point: lat={points[-1]['lat']}, lon={points[-1]['lon']}")
    
    kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>GPS Track</name>
<Style id="yellowLine">
<LineStyle>
<color>7f00ffff</color>
<width>4</width>
</LineStyle>
</Style>
<Style id="redStop">
<IconStyle>
<color>ff0000ff</color>
<scale>1.2</scale>
<Icon>
<href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href>
</Icon>
</IconStyle>
</Style>
<Style id="yellowTurn">
<IconStyle>
<color>ff00ffff</color>
<scale>1.2</scale>
<Icon>
<href>http://maps.google.com/mapfiles/kml/paddle/ylw-blank.png</href>
</Icon>
</IconStyle>
</Style>
'''
    
    kml_path = '''<Placemark>
<name>Route</name>
<styleUrl>#yellowLine</styleUrl>
<LineString>
<tessellate>1</tessellate>
<coordinates>
'''
    
    for point in points:
        kml_path += f"{point['lon']:.7f},{point['lat']:.7f},3\n"
    
    kml_path += '''</coordinates>
</LineString>
</Placemark>
'''
    
    stop_placemarks = ''
    for idx in stops:
        point = points[idx]
        stop_placemarks += f'''<Placemark>
<name>Stop</name>
<styleUrl>#redStop</styleUrl>
<Point>
<coordinates>{point['lon']:.7f},{point['lat']:.7f},3</coordinates>
</Point>
</Placemark>
'''
    
    turn_placemarks = ''
    for idx in turns:
        point = points[idx]
        turn_placemarks += f'''<Placemark>
<name>Left Turn</name>
<styleUrl>#yellowTurn</styleUrl>
<Point>
<coordinates>{point['lon']:.7f},{point['lat']:.7f},3</coordinates>
</Point>
</Placemark>
'''
    
    kml_footer = '''</Document>
</kml>'''
    
    with open(output_filename, 'w') as f:
        f.write(kml_header)
        f.write(kml_path)
        f.write(stop_placemarks)
        f.write(turn_placemarks)
        f.write(kml_footer)

def process_gps_file(input_file):
    print(f"Processing {input_file} ")
    
    points = read_gps_file(input_file)
    print(f"Read {len(points)} points")
    
    stops, turns = detect_stops_and_turns(points)
    print(f"Detected {len(stops)} stops and {len(turns)} left turns")
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{base_name}.kml"
    generate_kml(points, stops, turns, output_file)
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