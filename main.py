# CSCI 420 - GPS Processing Project
# @authors: Jacky Chan and Ethan Chang

#   Reads GPS NMEA data, parses coordinates, detects stops and left turns,
#   and generates a KML file with route and  markers.

# Instructions:
#   Place GPS files in Some_Example_GPS_Files/
#   Run with: python3 main.py


import os
import glob
import math
from datetime import datetime


def trim_stationary_edges(points):
    """
    Remove leading and trailing GPS points where the vehicle is not moving
    (speed < speed_threshold). Returns a sliced list of points.
    """

    if not points:
        return points

    n = len(points)
    first_moving = None
    last_moving = None

    # Find first index where speed >= threshold
    for i in range(n):

        if points[i].get('speed', 0.0) >= 1.0:

            first_moving = i

            break

    # Find last index where speed >= threshold
    for j in range(n - 1, -1, -1):

        if points[j].get('speed', 0.0) >= 1.0:

            last_moving = j

            break

    # If we never found any moving point, just return original or empty
    if first_moving is None or last_moving is None:
        print("Trip appears to have no movement (all points stationary).")
        return points

    if first_moving > 0 or last_moving < n - 1:
        print(f"Trimming {first_moving} leading stationary points "
              f"and {n - 1 - last_moving} trailing stationary points.")
    
    # Return only the moving portion of the trip 
    # GPS points without leading/trailing stationary points
    return points[first_moving:last_moving + 1]

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth.
    Returns distance in kilometers.
    """
    # only doing this in kilometers because of 2B saying:
    # Do not worry about the altitude. You can set that a 3 meters or something fixed.
    # so i set it to km for consistency. does it matter? prob not. can it be changed to miles? yea.
    # if it somehow relates to the tasks ahead, it can be easily converted as needed
    # we would also need to change the variables like KNOTS_TO_KMH = 1.852 to KNOTS_TO_MPH = 1.15078
    # and update other variables that are needed and related. so hopefully that wont happen.
    R = 6371.0  # Earth's radius in kilometers
    
    # conv degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # diff
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def calculate_trip_duration(points):
    if not points:

        # If the list is empty, there is no trip data to analyze

        print("No points available")
        return
    
    # Find the first point with a valid datetime
    start_dt = None
    for p in points:
        if p.get('datetime') is not None:
            start_dt = p['datetime']
            break

    # Find the last point with a valid datetime
    finish_dt = None
    for p in reversed(points):
        if p.get('datetime') is not None:
            finish_dt = p['datetime']
            break

    if start_dt is None or finish_dt is None:
        print("Cannot compute trip duration: missing datetime at start or end.")
        return
    
    # If they're strings, parse them
    if isinstance(start_dt, str):
        start_dt = datetime.fromisoformat(start_dt)
    if isinstance(finish_dt, str):
        finish_dt = datetime.fromisoformat(finish_dt)
    
    print(f"Start type: {type(start_dt)}, Finish type: {type(finish_dt)}")
    
    # Compute the duration as a timedelta (end time minus start time)
    duration = finish_dt - start_dt
    print(f"Trip Duration: {duration}")

    # ----------------------
    # part 5 time estimation
    # ----------------------
    speed_threshold = 5.0
    KNOTS_TO_KMH = 1.852
    
    started_moving = False
    stopped_moving = False
    estimated_start_gap = 0
    estimated_end_gap = 0
    
    # check if recording started while in motion
    check_window = min(5, len(points))
    start_speeds = [p['speed'] for p in points[:check_window] if p.get('speed') is not None]
    
    if start_speeds and sum(start_speeds) / len(start_speeds) >= speed_threshold:
        started_moving = True
        avg_start_speed_knots = sum(start_speeds) / len(start_speeds)
        avg_start_speed_kmh = avg_start_speed_knots * KNOTS_TO_KMH
        
        # look at distance over a larger window (first 10-20 points)
        if len(points) >= 10:
            # calculate distance from first point to 10th point
            dist_km = haversine_distance(
                points[0]['lat'], points[0]['lon'],
                points[9]['lat'], points[9]['lon']
            )
            
            if dist_km > 0.001 and avg_start_speed_kmh > 0:  # more than 1 meter
                # estimate based on average speed: assume we started 5-10 seconds before
                # use a conservative estimate of 5 seconds
                estimated_start_gap = 5.0
    
    # check if recording stopped while in motion
    end_speeds = [p['speed'] for p in points[-check_window:] if p.get('speed') is not None]
    
    if end_speeds and sum(end_speeds) / len(end_speeds) >= speed_threshold:
        stopped_moving = True
        avg_end_speed_knots = sum(end_speeds) / len(end_speeds)
        avg_end_speed_kmh = avg_end_speed_knots * KNOTS_TO_KMH
        
        # look at distance over a larger window (last 10-20 points)
        if len(points) >= 10:
            # calculate distance from 10th-to-last point to last point
            dist_km = haversine_distance(
                points[-10]['lat'], points[-10]['lon'],
                points[-1]['lat'], points[-1]['lon']
            )
            
            if dist_km > 0.001 and avg_end_speed_kmh > 0:  # more than 1 meter
                # estimate based on average speed: assume we continued 5-10 seconds after
                # use a conservative estimate of 5 seconds
                estimated_end_gap = 5.0
    
    total_estimated_gap = estimated_start_gap + estimated_end_gap
    
    # output results
    print("\nTRIP DURATION ANALYSIS\n")
    
    # report in motion
    if started_moving:
        print("GPS recording started while vehicle was in motion!")
        print(f"Estimated missing time at start: {estimated_start_gap:.2f} seconds")
    else:
        print("GPS recording started when vehicle was stationary")
    
    if stopped_moving:
        print("GPS recording stopped while vehicle was still in motion!")
        print(f"Estimated missing time at end: {estimated_end_gap:.2f} seconds")
    else:
        print("GPS recording stopped when vehicle was stationary")
   
    # Convert total duration into seconds as a float
    total_seconds = duration.total_seconds()

    # Convert seconds to minutes
    total_minutes = total_seconds / 60

    # Convert seconds to hours
    total_hours = total_seconds / 3600

    # reformatted from above
    print("\nRECORDED TRIP DURATION (from GPS timestamps):")
    print(f"Start time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End time:   {finish_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration:   {total_seconds:.2f} seconds")
    print(f"            {total_minutes:.2f} minutes")
    print(f"            {total_hours:.2f} hours")
    
    # report estimated actual duration (if missing time detected)
    if total_estimated_gap > 0:
        estimated_total_seconds = total_seconds + total_estimated_gap
        print()
        print("ESTIMATED ACTUAL TRIP DURATION (including missing time):")
        print(f"  Missing time at start: {estimated_start_gap:.2f} seconds")
        print(f"  Missing time at end:   {estimated_end_gap:.2f} seconds")
        print(f"  Total missing time:    {total_estimated_gap:.2f} seconds")
        print(f"  Estimated total:       {estimated_total_seconds:.2f} seconds")
        print(f"                         {estimated_total_seconds/60:.2f} minutes")
        print(f"                         {estimated_total_seconds/3600:.2f} hours")

def split_double_sentences(line):
    """
    Part C: Detect and split Arduino double-sentence lines.
    This function detects this anomaly and splits them into separate sentences.
    Returns: list of sentence strings (usually 1, but 2 if double-sentence detected)
    """
    # Look for the pattern: $GPRMC or $GPGGA followed by another $GP sequence
    # without a proper line break
    sentences = []
    
    # Check if line contains multiple NMEA sentences jammed together
    # Pattern: $GPxxxx....*xx$GPyyyy (sentence ends with *checksum then immediately starts new $GP)
    # Example: $GPRMC,221249.250,A,4305.1467,N,07740.8187,W,0.54,313.60,110925$GPGGA,221249.500,4305.1466,N,07740.8188,W,1,04,2.05,75.7,M,-34.4,M,,*67
    # This example came from 2025_09_11__221355_gps_file.txt Line 23
    import re
    
    # Find all NMEA sentence starts ($GPxxx)
    matches = list(re.finditer(r'\$GP\w{3}', line))
    
    if len(matches) == 1:
        # Normal case: only one sentence
        sentences.append(line)
    elif len(matches) >= 2:
        # Multiple sentences jammed together
        for i, match in enumerate(matches):
            start = match.start()
            if i < len(matches) - 1:
                # Get up to the start of the next sentence
                end = matches[i + 1].start()
                sentence = line[start:end].rstrip('*')  # Remove trailing checksum separator if any
            else:
                # Last sentence: take to end of line
                sentence = line[start:]
            
            if sentence.strip():
                sentences.append(sentence.strip())
    else:
        # No proper sentence found, return original line
        sentences.append(line)
    
    return sentences


def parse_nmea_coordinate(coord_str, direction):
    """
    Converts NMEA coordinate format to decimal degrees. (DDMM.MMMM)
    direction: 'N', 'S', 'E', 'W'
    """

    # If the coordinate string or direction is missing, we cannot parse it
    if not coord_str or not direction:

        return None
    
    try:

        # Convert the coordinate string to a float, e.g. "4307.1234"
        coord_float = float(coord_str)

        # Extract degrees and minutes
        degrees = int(coord_float / 100)

        # Extract minutes
        minutes = coord_float - (degrees * 100)

        # Convert to decimal degrees
        decimal = degrees + (minutes / 60)

        # Apply negative sign for South and West directions
        if direction in ['S', 'W']:

            decimal = -decimal

        return decimal
    
    except:

        return None

def parse_gprmc(line):
    """
    Parse a $GPRMC sentence.
    Extract latitude, longitude, speed (knots), heading, and datetime.
    Returns a dictionary or None if invalid.
    (time_str, lat_str, lat_dir, lon_str, lon_dir, speed_knots, course, date_str)
    """
    
    # Split the NMEA sentence by commas into its fields    
    # Example: $GPRMC,144904.500,A,4308.4726,N,07726.4348,W,0.16,53.46,010525,,,A*42
    parts = line.strip().split(',')

    if len(parts) < 10 or parts[2] != 'A':

        return None
    
    # Extract individual fields by their positions in the GPRMC sentence
    time_str = parts[1]      # UTC time (hhmmss.sss)
    lat_str = parts[3]       # Latitude in NMEA format (DDMM.MMMM)
    lat_dir = parts[4]       # Latitude direction 'N' or 'S'
    lon_str = parts[5]       # Longitude in NMEA format (DDDMM.MMMM)
    lon_dir = parts[6]       # Longitude direction 'E' or 'W'
    speed_knots = parts[7]   # Speed over ground in knots
    course = parts[8]        # Course over ground (heading) in degrees
    date_str = parts[9]      # Date (ddmmyy)
    
    if not all([time_str, lat_str, lat_dir, lon_str, lon_dir, date_str]):
        return None
    
    # Convert NMEA latitude and longitude to decimal degrees
    lat = parse_nmea_coordinate(lat_str, lat_dir)
    lon = parse_nmea_coordinate(lon_str, lon_dir)
    
    if lat is None or lon is None:
        return None
    
    try:
        # Convert speed from string to float; if empty, default to 0.0
        speed = float(speed_knots) if speed_knots else 0.0
    except:
        speed = 0.0
    
    try:
        heading = float(course) if course else None
    except:
        heading = None
    
    try:
        # Starting date time parsing
        dt = datetime.strptime(date_str + time_str.split('.')[0], '%d%m%y%H%M%S')
    except:
        dt = None
    
    # Return a dictionary representing this GPS point
    return {
        'lat': lat,          # Latitude in decimal degrees
        'lon': lon,          # Longitude in decimal degrees
        'speed': speed,      # Speed in knots
        'heading': heading,  # Heading in degrees (may be None)
        'datetime': dt       # datetime object or None
    }

def parse_gpgga(line):
    """
    Parse a $GPGGA sentence.
    Extract latitude and longitude.
    Returns a dictionary or None if invalid.
    """

    # Split the GPGGA sentence into comma-separated fields
    # Example: $GPGGA,144904.750,4308.4726,N,07726.4349,W,1,05,1.80,162.6,M,-34.4,M,,*57
    parts = line.strip().split(',')

    if len(parts) < 10:
        return None
    
    # Time is present but not used here; kept for reference
    time_str = parts[1]
    # Latitude string and direction
    lat_str = parts[2]
    lat_dir = parts[3]
    # Longitude string and direction
    lon_str = parts[4]
    lon_dir = parts[5]
    
    if not all([lat_str, lat_dir, lon_str, lon_dir]):
        return None
    
    # Convert NMEA coordinates into decimal degrees
    lat = parse_nmea_coordinate(lat_str, lat_dir)
    lon = parse_nmea_coordinate(lon_str, lon_dir)
    
    if lat is None or lon is None:
        return None

    # Parse fix quality, number of satellites, and HDOP when available
    try:
        fix_quality = int(parts[6]) if parts[6] else 0
    except:
        fix_quality = 0

    try:
        num_sats = int(parts[7]) if parts[7] else 0
    except:
        num_sats = 0

    try:
        hdop = float(parts[8]) if parts[8] else None
    except:
        hdop = None

    # Return coordinates and basic quality metrics
    return {
        'lat': lat,
        'lon': lon,
        'fix': fix_quality,
        'sats': num_sats,
        'hdop': hdop
    }

def read_gps_file(filename):
    """
    Read GPS .txt file line by line.
    Uses GPRMC to track points.
    Returns a list of points with lat, lon, speed, heading, datetime.
    """

    points = []  # List to store all parsed GPS points
    double_sentence_count = 0  # Track how many double-sentences we encounter

    # Open the file in read mode, using latin-1 encoding to handle special characters
    with open(filename, 'r', encoding='latin-1') as f:
        
        last_gpgga = None
        for line in f:
            # Remove leading/trailing whitespace from the line
            line = line.strip()

            # Skip empty lines or lines that do not start with "$GP" (non-NMEA)
            if not line or not line.startswith('$GP'):
                continue
            
            # Part C: Split double-sentences on the same line
            sentences = split_double_sentences(line)
            
            # If we got multiple sentences, we found a double-sentence anomaly
            if len(sentences) > 1:
                double_sentence_count += 1
            
            # Parse each sentence (usually 1, but 2 if double-sentence was split)
            for sentence in sentences:
                # If the line is a GPRMC sentence, we parse it for full GPS data
                if sentence.startswith('$GPRMC'):
                    data = parse_gprmc(sentence)
                    # Attach most recent GPGGA quality info if available
                    if data and last_gpgga:
                        # Ensure keys exist but don't overwrite core lat/lon/datetime
                        data['hdop'] = last_gpgga.get('hdop')
                        data['sats'] = last_gpgga.get('sats')
                        data['fix'] = last_gpgga.get('fix')
                    # Only add the point if parsing was successful (data is not None)
                    if data:
                        points.append(data)
                elif sentence.startswith('$GPGGA'):
                    # Parse and remember latest GPGGA quality metrics to attach to next GPRMC
                    gga = parse_gpgga(sentence)
                    if gga:
                        last_gpgga = gga
    
    # Report double-sentence fixes if any were found
    if double_sentence_count > 0:
        print(f"  Part C: Found and split {double_sentence_count} double-sentence anomalies")
    
    # Return the list of parsed GPS points
    return points


def normalize_angle(angle):
    """
    Normalize heading angle to [0, 360) degrees.
    Prevent negative angles and angles >= 360.
    """
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle

def angle_difference(prev_heading, curr_heading):
    """
    Computer shortest signed angular defference between two ehadings.
    """

    # Normalize previous heading into [0, 360)
    prev = normalize_angle(prev_heading)
    # Normalize current heading into [0, 360)
    curr = normalize_angle(curr_heading)
    
    # Initial difference is current minus previous
    diff = curr - prev
    
    if diff < -180:
        diff += 360
    elif diff > 180:
        diff -= 360
    
    return diff

def filter_position_outliers(points, max_speed_kmh=200.0):
    """
    Part D: Filter out GPS points that imply impossible speeds between samples.
    
    If the distance between consecutive points, given the time difference, would
    require the car to travel faster than max_speed_kmh, we treat the newer
    point as junk (likely an antenna / GPS glitch) and skip it.
    
    Lane change can also count as left turn!
    """
    if len(points) < 2:
        return points
    
    cleaned = [points[0]]
    removed_count = 0
    
    for i in range(1, len(points)):
        prev = cleaned[-1]
        curr = points[i]
 
        if prev.get('datetime') is None or curr.get('datetime') is None:

            cleaned.append(curr)
            continue
        
        dt = (curr['datetime'] - prev['datetime']).total_seconds()

        if dt <= 0:
            removed_count += 1
            continue
        
        dist_km = haversine_distance(prev['lat'], prev['lon'],
                                     curr['lat'], curr['lon'])
        speed_kmh = dist_km / (dt / 3600.0)
        
        if speed_kmh > max_speed_kmh:
            removed_count += 1
            continue
        
        cleaned.append(curr)
    
    if removed_count > 0:
        print(f"  Filtered {removed_count} position outliers (Part D, "
              f"speed > {max_speed_kmh} km/h). Remaining: {len(cleaned)} points.")
    
    return cleaned


def filter_by_quality(points, hdop_threshold=3.0, min_sats=4, require_fix=True):
    """
    Part E: Filter points by HDOP, satellite count, and fix quality.

    If a point lacks all quality fields (`hdop`, `sats`, `fix`), we keep it.

    Otherwise we remove points.
    Returns the filtered list of points.
    """
    if not points:
        return points

    kept = []
    removed = 0
    for p in points:
        hdop = p.get('hdop')
        sats = p.get('sats')
        fix = p.get('fix')

        # If we lack any quality info, keep the point
        if hdop is None and sats is None and fix is None:
            kept.append(p)
            continue

        if hdop is not None and hdop > hdop_threshold:
            removed += 1
            continue
        if sats is not None and sats < min_sats:
            removed += 1
            continue
        if require_fix and fix is not None and fix < 1:
            removed += 1
            continue

        kept.append(p)

    if removed > 0:
        print(f"  Part E: Filtered {removed} points by HDOP/sats/fix quality")

    return kept

def detect_stops_and_turns(points):
    """
    Analyze GPS points to detect:
    - Stops: speed < 1 knot
    - Left Turns: average speed > 5 knots and cumulative left turn > 25 degrees
    Returns two lists: stop indices and left turn indices.
    """

    stops = []  # List of indices in 'points' where stops occur
    turns = []  # List of indices in 'points' where left turns occur
    
    # Speed threshold (knots) below which we consider the car stopped
    speed_threshold = 1.0
    # Minimum average speed (knots) in window for heading-based turn detection
    min_speed_for_heading = 5.0
    # Minimum cumulative left-turn angle (degrees) to flag a left turn
    turn_threshold = 25
    # Number of points in the sliding window used to detect turns
    window_size = 10

    for i in range(len(points)):
        # Check if current point is below the stop speed threshold
        if points[i]['speed'] < speed_threshold:
            # To avoid marking repeated stops, only flag when coming from moving state
            if i > 0 and points[i-1]['speed'] >= speed_threshold:
                # Record the index where the car transitions to a stop
                stops.append(i)
    
    for i in range(window_size, len(points)):

        # Compute average speed in the sliding window [i - window_size, i]
        avg_speed = sum(p['speed'] for p in points[i-window_size:i+1]) / (window_size + 1)
        
        if avg_speed < min_speed_for_heading:
            continue
        
        # Index of the first point in the window
        start_idx = i - window_size
        
        if points[start_idx]['heading'] is None or points[i]['heading'] is None:
            continue
        
        # Filter only points in the window where the car is moving fast enough
        # and have a valid heading
        moving_points = [p for p in points[start_idx:i+1] if p['speed'] > min_speed_for_heading and p['heading'] is not None]
        
        if len(moving_points) < 3:
            continue

        # Compute total heading change from the first to last point in this moving subset
        total_turn = angle_difference(moving_points[0]['heading'], moving_points[-1]['heading'])
        
        if total_turn < -turn_threshold:
            # Check if we have already marked a nearby turn to avoid duplicates
            already_marked = False
            for t in turns:
                # If an existing turn index is within the window, treat as duplicate
                if abs(t - i) < window_size:
                    already_marked = True
                    break
            
            if not already_marked:
                turns.append(i)
    
    return stops, turns

def generate_kml(points, stops, turns, output_filename):
    """
    Create KML file containing:
        - Route as a LineString
        - Stop markers as red icons
        - Left turn markers as yellow icons
    Save output file into .kml file
    """
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
    """
    Find all GPS files in specified folder and process each one.
    For each file:
        - Read and parse GPS data
        - Detect stops and left turns
        - Generate KML file with route and markers
    """
    print(f"Processing {input_file} ")
    
    points = read_gps_file(input_file)
    print(f"  Read {len(points)} raw points")
    
    points = trim_stationary_edges(points)
    print(f"  After trimming stationary edges: {len(points)} points")
    
    points = filter_position_outliers(points, max_speed_kmh=200.0)

    points = filter_by_quality(points, hdop_threshold=3.0, min_sats=4, require_fix=True)

    stops, turns = detect_stops_and_turns(points)
    print(f"Detected {len(stops)} stops and {len(turns)} left turns")
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{base_name}.kml"
    generate_kml(points, stops, turns, output_file)
    print(f"Generated {output_file}")
    print()

    calculate_trip_duration(points)

def main():

    # Reads GPS files from Some_Example_GPS_Files/ and processes them
    gps_files = glob.glob("Some_Example_GPS_Files/*.txt")
    
    if not gps_files:
        print("No GPS files found in Some_Example_GPS_Files/")
        return
    
    for gps_file in gps_files:
        process_gps_file(gps_file)

if __name__ == "__main__":
    main()