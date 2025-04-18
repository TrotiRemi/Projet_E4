import pandas as pd
import requests
import time

# Fichier d'entrée (CSV original sans coordonnées)
INPUT_CSV = "avignon_tourism/activites.csv"

# Fichier de sortie (CSV avec coordonnées GPS)
OUTPUT_CSV = "avignon_tourism/activites_with_coords.csv"

# Fonction pour obtenir les coordonnées GPS via l'API Nominatim (OpenStreetMap)
def get_coordinates(address):
    url = f'https://nominatim.openstreetmap.org/search?q={address},Avignon&format=json'
    headers = {'User-Agent': 'GeoLocator/1.0 (your_email@example.com)'}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Erreur HTTP {response.status_code} pour {address}")
        return None, None

    try:
        data = response.json()
        if len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
        else:
            print(f"⚠️ Adresse non trouvée : {address}")
            return None, None
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des coordonnées pour {address} : {str(e)}")
        return None, None

# Charger le CSV des restaurants
df = pd.read_csv(INPUT_CSV)

# Vérifier que la colonne "address" existe
if "adresse" not in df.columns:
    raise ValueError("🚨 Le fichier CSV ne contient pas de colonne 'adresse'.")

# Ajouter les colonnes pour stocker les coordonnées
df["latitude"] = None
df["longitude"] = None

# Traiter chaque adresse et obtenir les coordonnées
for index, row in df.iterrows():
    address = row["adresse"]
    
    # Obtenir les coordonnées
    lat, lon = get_coordinates(address)
    
    # Si les coordonnées sont valides, les stocker
    if lat is not None and lon is not None:
        df.at[index, "latitude"] = lat
        df.at[index, "longitude"] = lon
        print(f"✅ Coordonnées trouvées pour {address} : {lat}, {lon}")
    else:
        print(f"❌ Impossible d'obtenir les coordonnées pour {address}")

    # Pause pour éviter d'être bloqué par l'API Nominatim (max ~1 requête/sec)
    time.sleep(1)

# Sauvegarder le fichier avec les nouvelles coordonnées
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

print(f"\n🎉 Fichier CSV mis à jour et sauvegardé : {OUTPUT_CSV}")
