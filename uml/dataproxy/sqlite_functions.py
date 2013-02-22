"""
    Simple functions added to extend the sqlite3 query language. 

    By calling create_function on the sqlite3 connection object
    it is possible to provide extra functionality to the dataproxy.
"""
import math

def distance_on_spherical_earth(lat1, long1, lat2, long2):
    """
        This Public Domain code taken from 
        http://www.johndcook.com/python_longitude_latitude.html
        
        The following code returns the distance between to locations based on
        each point's longitude and latitude in kilometres.

        Latitude is measured in degrees north of the equator; southern locations 
        have negative latitude. Similarly, longitude is measured in degrees east 
        of the Prime Meridian. A location 10 west of the Prime Meridian, for 
        example, could be expressed as either 350 east or as -10 east.    
    """
    try:
        lat1 = float(lat1)
        lat2 = float(lat2)
        long1 = float(long1)
        long2 = float(long2)
    except Exception, e:
        raise
        
    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
        
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
        
    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
        
    # Compute spherical distance from spherical coordinates.
        
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
    
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
           math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )

    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc * float(6371)

if __name__ == '__main__':
    # Simple test
    print distance_on_spherical_earth(51.885, 0.235, 49.008, 2.549)
    print distance_on_spherical_earth('51.885', '0.235', '49.008', '2.549')
    print distance_on_spherical_earth('51.885', '0.235', 'hello', 0)    
    