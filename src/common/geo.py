"""Distance helpers for the resource finder."""

from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in kilometres.

    Good to within ~0.5% - far better than needed to decide which of two
    trauma centres is nearer.
    """
    lat1, lon1, lat2, lon2 = (float(v) for v in (lat1, lon1, lat2, lon2))
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    # Clamp: floating point can push `a` a hair above 1 for antipodal points,
    # and sqrt of a negative would raise.
    a = min(1.0, max(0.0, a))
    return round(2 * EARTH_RADIUS_KM * asin(sqrt(a)), 2)


def extract_point(item):
    """(lat, lon) from a resource's geo block, or None if unusable.

    Records without coordinates are normal - an NGO or a government scheme has
    no single location - so this returns None rather than raising.
    """
    geo = item.get("geo")
    if not isinstance(geo, dict):
        return None
    lat, lon = geo.get("lat"), geo.get("lon")
    if lat is None or lon is None:
        return None
    try:
        lat = float(lat) if not isinstance(lat, Decimal) else float(lat)
        lon = float(lon) if not isinstance(lon, Decimal) else float(lon)
    except (TypeError, ValueError):
        return None
    if lat != lat or lon != lon:  # NaN
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon
