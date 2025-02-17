import folium
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Fonction pour obtenir les coordonnées GPS d'une adresse via Nominatim (OpenStreetMap)
def get_coordinates(address):
    url = f'https://nominatim.openstreetmap.org/search?q={address},Avignon&format=json'
    headers = {'User-Agent': 'GeoLocator/1.0 (your_email@example.com)'}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise ValueError(f"Erreur lors de la requête : {response.status_code}")
    
    try:
        data = response.json()
        if len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
        else:
            raise ValueError(f"Adresse {address} non trouvée.")
    except ValueError:
        raise ValueError("La réponse de l'API n'a pas pu être interprétée.")

# Fonction pour calculer l'itinéraire à pied via l'API OSRM
def get_route(start_coords, end_coords):
    # Changer 'driving' à 'walking' pour obtenir un itinéraire à pied
    url = f'http://router.project-osrm.org/route/v1/walking/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=geojson'
    response = requests.get(url)
    
    if response.status_code != 200:
        raise ValueError(f"Erreur lors de l'API OSRM : {response.status_code}")
    
    data = response.json()
    if data['routes']:
        route = data['routes'][0]['geometry']
        return route
    else:
        raise ValueError("Impossible de calculer l'itinéraire.")

# Fonction pour afficher la carte et l'itinéraire sur Folium
def create_map(start_address, end_address):
    start_coords = get_coordinates(start_address)
    end_coords = get_coordinates(end_address)
    route = get_route(start_coords, end_coords)
    
    m = folium.Map(location=start_coords, zoom_start=14)
    folium.Marker(start_coords, popup=f"Départ: {start_address}").add_to(m)
    folium.Marker(end_coords, popup=f"Arrivée: {end_address}").add_to(m)
    
    folium.PolyLine(locations=[(lat, lon) for lon, lat in route['coordinates']], color='blue', weight=4.5, opacity=0.7).add_to(m)
    
    # Enregistrer la carte sous forme de fichier HTML
    map_filename = "static/itineraire_avignon.html"
    m.save(map_filename)
    
    return map_filename

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        start_address = request.form["start_address"]
        end_address = request.form["end_address"]
        
        try:
            map_filename = create_map(start_address, end_address)
            return render_template("index.html", map_file=map_filename, start_address=start_address, end_address=end_address)
        except Exception as e:
            return render_template("index.html", error=str(e))
    
    return render_template("index.html", map_file=None)

if __name__ == "__main__":
    app.run(debug=True)
