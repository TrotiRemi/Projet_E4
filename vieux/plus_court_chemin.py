import pandas as pd
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import time
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Init géolocalisation
geolocator = Nominatim(user_agent="geo_matrix_app", timeout=10)

def normalize_address(address):
    city_keywords = ["avignon", "villeneuve"]
    if not any(city in address.lower() for city in city_keywords):
        return address.strip() + ", Avignon, France"
    return address

def get_coordinates(address, cache):
    if address in cache:
        return cache[address]
    try:
        location = geolocator.geocode(address)
        if location:
            coords = (location.latitude, location.longitude)
            cache[address] = coords
            return coords
        else:
            logging.warning(f"Adresse introuvable : {address}")
    except Exception as e:
        logging.error(f"Erreur de géocodage pour {address} : {e}")
    cache[address] = None
    return None

def load_all_addresses():
    df_activites = pd.read_csv("activite_corrigees.csv")
    df_restaurants = pd.read_csv("restaurants_corriges.csv")

    adresses_activites = df_activites[["adresse", "nom"]].dropna()
    adresses_restaurants = df_restaurants[["address", "name"]].dropna()

    activite_list = [(normalize_address(row["adresse"]), row["nom"], "Activité") for _, row in adresses_activites.iterrows()]
    restaurant_list = [(normalize_address(row["address"]), row["name"], "Restaurant") for _, row in adresses_restaurants.iterrows()]

    all_adresses = list(set(activite_list + restaurant_list))
    return all_adresses

def build_enriched_matrix(named_addresses):
    coords_cache = {}
    coords = {}

    logging.info("Géocodage des adresses...")
    for adr, _, _ in named_addresses:
        coords[adr] = get_coordinates(adr, coords_cache)
        time.sleep(1)

    valid_entries = [(adr, nom, typ) for adr, nom, typ in named_addresses if coords[adr] is not None]

    rows = []
    logging.info("Calcul des distances et temps enrichis...")
    for i in range(len(valid_entries)):
        for j in range(len(valid_entries)):
            addr1, name1, type1 = valid_entries[i]
            addr2, name2, type2 = valid_entries[j]
            coord1 = coords[addr1]
            coord2 = coords[addr2]

            if addr1 == addr2:
                distance_m = 0
                time_min = 0
            else:
                distance_km = geodesic(coord1, coord2).km
                distance_m = int(distance_km * 1000)
                time_min = int((distance_km / 5) * 60)

            rows.append({
                "from_name": name1,
                "from_address": addr1,
                "from_type": type1,
                "to_name": name2,
                "to_address": addr2,
                "to_type": type2,
                "distance_m": distance_m,
                "time_min": time_min
            })

    return pd.DataFrame(rows)

if __name__ == "__main__":
    adresses_nommees = load_all_addresses()
    enriched_df = build_enriched_matrix(adresses_nommees)

    enriched_df.to_csv("matrice_distances_enrichie.csv", index=False)
    logging.info("Matrice enrichie enregistrée avec succès.")
