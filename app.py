import folium
import requests
import pandas as pd
from flask import Flask, render_template, request
from concurrent.futures import ThreadPoolExecutor
from geopy.distance import geodesic
from functools import lru_cache

app = Flask(__name__)

def filter_nearby_places(start_coords, df, max_distance_km=3):
    """Filtre les lieux (restaurants/activités) à moins de max_distance_km du point de départ."""
    filtered_df = df.copy()
    filtered_df["distance"] = filtered_df.apply(
        lambda row: geodesic(start_coords, (row["latitude"], row["longitude"])).km, axis=1
    )
    return filtered_df[filtered_df["distance"] <= max_distance_km]

def parallel_get_route(locations):
    """Calcule les routes en parallèle pour accélérer le traitement."""
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda loc: get_route(*loc), locations))
    return results

# Charger le fichier CSV avec les coordonnées GPS des restaurants et activités
def load_csv_with_coords(input_file):
    """Charge un fichier CSV contenant les coordonnées des lieux."""
    df = pd.read_csv(input_file)
    if "latitude" not in df.columns or "longitude" not in df.columns:
        raise ValueError(f"🚨 Le fichier {input_file} ne contient pas les colonnes 'latitude' et 'longitude'.")
    return df

# Charger les données des restaurants et des activités
restaurants_df = load_csv_with_coords("avignon_tourism/restaurant_with_coords.csv")
activites_df = load_csv_with_coords("avignon_tourism/activites_with_coords.csv")

# Fonction pour récupérer les coordonnées d'un restaurant
def get_precomputed_restaurant_coordinates(address):
    row = restaurants_df[restaurants_df["address"] == address]
    if not row.empty:
        return float(row["latitude"].values[0]), float(row["longitude"].values[0])
    return None, None

# Fonction pour récupérer les coordonnées d'une activité
def get_precomputed_activity_coordinates(address):
    row = activites_df[activites_df["adresse"] == address]
    if not row.empty:
        return float(row["latitude"].values[0]), float(row["longitude"].values[0])
    return None, None

# Fonction pour récupérer les coordonnées GPS via l'API Nominatim (pour départ et arrivée uniquement)
def get_coordinates(address):
    url = f'https://nominatim.openstreetmap.org/search?q={address},Avignon&format=json'
    headers = {'User-Agent': 'GeoLocator/1.0 (your_email@example.com)'}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(f"❌ Erreur HTTP {response.status_code} pour {address}")

    try:
        data = response.json()
        if len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon'])
        else:
            raise ValueError(f"❌ Adresse '{address}' non trouvée.")
    except Exception as e:
        raise ValueError(f"❌ Erreur lors de la récupération des coordonnées pour {address} : {str(e)}")

# Fonction pour récupérer l'itinéraire et la distance via OSRM
route_cache = {}

def get_route(start_coords, end_coords):
    """Obtient l'itinéraire à pied via OSRM et retourne la distance."""
    cache_key = (start_coords, end_coords)

    # Vérification dans le cache
    if cache_key in route_cache:
        return route_cache[cache_key]

    # Vérification des coordonnées avant la requête OSRM
    if not all(start_coords) or not all(end_coords):
        raise ValueError(f"❌ Coordonnées invalides : {start_coords} → {end_coords}")

    url = f'http://router.project-osrm.org/route/v1/walking/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=geojson&steps=true'
    
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Erreur OSRM: {response.status_code} - URL: {url}")

    try:
        data = response.json()
        if 'routes' in data and data['routes']:
            route_info = data['routes'][0]
            distance_km = route_info['distance'] / 1000  # Convertir en km
            route_cache[cache_key] = (route_info['geometry']['coordinates'], round(distance_km, 2))
            return route_cache[cache_key]
        else:
            raise ValueError("Aucun itinéraire trouvé.")
    except Exception as ve:
        raise ValueError(f"Erreur de lecture de l'itinéraire OSRM : {str(ve)}")

# Fonction pour calculer la meilleure activité
def get_best_activity(start_coords, end_coords):
    """Trouve l'activité qui augmente le moins la distance du trajet."""
    best_activity_coords, best_activity_info = None, None
    min_additional_distance = float('inf')

    for _, row in activites_df.iterrows():
        if pd.isna(row["latitude"]) or pd.isna(row["longitude"]):
            continue  # Ignore cette activité si les coordonnées sont NaN

        activity_coords = (row["latitude"], row["longitude"])
        route1, dist1 = get_route(start_coords, activity_coords)
        route2, dist2 = get_route(activity_coords, end_coords)

        additional_distance = dist1 + dist2
        if additional_distance < min_additional_distance:
            min_additional_distance = additional_distance
            best_activity_coords = activity_coords
            best_activity_info = row

    return best_activity_coords, best_activity_info

# Fonction pour calculer le meilleur restaurant
def get_best_restaurant(start_coords, end_coords):
    """Trouve le restaurant qui augmente le moins la distance du trajet, en filtrant les plus proches."""
    best_restaurant_coords, best_restaurant_info = None, None
    min_additional_distance = float('inf')

    nearby_restaurants = filter_nearby_places(start_coords, restaurants_df)

    for _, row in nearby_restaurants.iterrows():
        restaurant_coords = (row["latitude"], row["longitude"])
        route1, dist1 = get_route(start_coords, restaurant_coords)
        route2, dist2 = get_route(restaurant_coords, end_coords)

        additional_distance = dist1 + dist2
        if additional_distance < min_additional_distance:
            min_additional_distance = additional_distance
            best_restaurant_coords = restaurant_coords
            best_restaurant_info = row

    return best_restaurant_coords, best_restaurant_info


# Fonction principale pour afficher la carte et optimiser l'itinéraire
def create_map(start_address, end_address, include_restaurant=False, include_activity=False):
    """Génère une carte avec itinéraire optimisé incluant restaurant et activité."""
    start_coords = get_coordinates(start_address)
    end_coords = get_coordinates(end_address)

    best_restaurant_coords, best_restaurant_info = None, None
    best_activity_coords, best_activity_info = None, None

    if include_restaurant:
        best_restaurant_coords, best_restaurant_info = get_best_restaurant(start_coords, end_coords)

    if include_activity:
        best_activity_coords, best_activity_info = get_best_activity(start_coords, end_coords)

    # Construire la liste des étapes valides
    valid_waypoints = [start_coords]
    if best_restaurant_coords:
        valid_waypoints.append(best_restaurant_coords)
    if best_activity_coords:
        valid_waypoints.append(best_activity_coords)
    valid_waypoints.append(end_coords)

    # Exécuter les requêtes OSRM en parallèle pour accélérer le traitement
    locations = [(valid_waypoints[i], valid_waypoints[i + 1]) for i in range(len(valid_waypoints) - 1)]
    routes_distances = parallel_get_route(locations)

    # Construire l'itinéraire final
    route_segments = []
    total_distance = 0
    for segment, distance in routes_distances:
        route_segments.extend(segment)
        total_distance += distance

    # Générer la carte Folium
    m = folium.Map(location=start_coords, zoom_start=14)
    folium.Marker(start_coords, popup=f"Départ: {start_address}").add_to(m)
    folium.Marker(end_coords, popup=f"Arrivée: {end_address}").add_to(m)

    if best_restaurant_coords:
        folium.Marker(best_restaurant_coords, popup=f"Restaurant: {best_restaurant_info['name']}<br>Distance: {total_distance} km",
                      icon=folium.Icon(color='red', icon='cutlery')).add_to(m)

    if best_activity_coords:
        folium.Marker(best_activity_coords, popup=f"Activité: {best_activity_info['nom']}<br>Distance: {total_distance} km",
                      icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)

    folium.PolyLine([(lat, lon) for lon, lat in route_segments], color='blue', weight=4.5, opacity=0.7).add_to(m)
    m.save("static/itineraire_avignon.html")
    return "static/itineraire_avignon.html"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        start_address = request.form["start_address"]
        end_address = request.form["end_address"]
        include_restaurant = "restaurant" in request.form  # Vérifie si la case est cochée
        include_activity = "activity" in request.form  # Vérifie si la case est cochée

        try:
            map_filename = create_map(start_address, end_address, include_restaurant, include_activity)
            return render_template("index.html", map_file=map_filename, start_address=start_address, end_address=end_address)
        except Exception as e:
            return render_template("index.html", error=str(e))

    return render_template("index.html", map_file=None)


if __name__ == "__main__":
    app.run(debug=True)
