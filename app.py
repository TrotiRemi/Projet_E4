from flask import Flask, render_template, request, redirect, flash
import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from functools import lru_cache

app = Flask(__name__)
app.secret_key = "votre_clé_secrète"

# Chargement des données
df_activites = pd.read_csv("activite.csv")
df_restaurants = pd.read_csv("restaurants.csv")

# Géolocalisation
geolocator = Nominatim(user_agent="planning_app")
@lru_cache(maxsize=1024)
def get_coords(address):
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
    except:
        return None
    return None

def calculate_walking_minutes(addr1, addr2):
    coords1 = get_coords(addr1)
    coords2 = get_coords(addr2)
    if coords1 and coords2:
        distance_km = geodesic(coords1, coords2).km
        walking_speed_kmh = 5
        time_hours = distance_km / walking_speed_kmh
        return int(time_hours * 60)
    return 15

# Adresse centrale d'Avignon pour démarrer les trajets
adresse_depart = "Place de l'Horloge, Avignon, France"
coord_centre = get_coords(adresse_depart)
def get_min_price(pricing_str):
    try:
        if not isinstance(pricing_str, str) or not pricing_str.strip():
            return None
        prixs = []
        for prix in pricing_str.split(","):
            cleaned = prix.replace("€", "").replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
            if cleaned:
                prixs.append(float(cleaned))
        return min(prixs) if prixs else None
    except:
        return None

all_themes = set()
for themes in df_activites["thèmes"].dropna():
    for theme in themes.split(", "):
        all_themes.add(theme)
themes_disponibles = sorted(all_themes)

all_specs = set()
for specs in df_restaurants["specialties"].dropna():
    for s in specs.split(","):
        all_specs.add(s.strip())
types_restaurants = sorted(all_specs)

df_restaurants["prix_min"] = df_restaurants["pricing"].apply(get_min_price)
df_restaurants = df_restaurants[df_restaurants["prix_min"].notna()]

def jour_to_label(abbr):
    return {
        "L": "Lundi", "M": "Mardi", "ME": "Mercredi",
        "J": "Jeudi", "V": "Vendredi", "S": "Samedi", "D": "Dimanche"
    }.get(abbr, "Lundi")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        jour = request.form.get("jour", "")
        jour_label = jour_to_label(jour)
        debut_heure = request.form.get("debut_heure", "")
        fin_heure = request.form.get("fin_heure", "")
        budget = request.form.get("budget", "")
        nombre_activites = int(request.form.get("nombre_activites", 0))
        nombre_restaurants = int(request.form.get("nombre_restaurants", 0))
        themes_selectionnes = request.form.getlist("themes")
        types_selectionnes = request.form.getlist("types_restaurants")

        if not budget:
            flash("Veuillez renseigner un budget.", "danger")
            return redirect("/")
        if not jour_label:
            flash("Veuillez sélectionner un jour de la semaine.", "danger")
            return redirect("/")

        budget = float(budget)
        debut_heure = int(debut_heure) if debut_heure else 10
        fin_heure = int(fin_heure) if fin_heure else 23

        jour_abbr_map = {
            "Lundi": "L", "Mardi": "M", "Mercredi": "ME",
            "Jeudi": "J", "Vendredi": "V", "Samedi": "S", "Dimanche": "D"
        }
        jour_abbr = jour_abbr_map.get(jour_label, "L")

        # --- Restaurants ---
        restaurants_filtres = df_restaurants.copy()
        restaurants_filtres["rating"] = restaurants_filtres["rating"].replace("N/D", "0").astype(float)
        restaurants_filtres.loc[restaurants_filtres["rating"] > 10, "rating"] = 0
        restaurants_filtres = restaurants_filtres[restaurants_filtres["prix_min"] <= budget]
        restaurants_filtres = restaurants_filtres[restaurants_filtres[jour_label].str.lower() != "fermé"]
        if types_selectionnes:
            restaurants_filtres = restaurants_filtres[restaurants_filtres["specialties"].apply(
                lambda x: any(t in x for t in types_selectionnes if isinstance(x, str)))]
        restaurants_filtres = restaurants_filtres.sort_values(by="rating", ascending=False).to_dict(orient="records")

        # --- Activités ---
        activites_filtrees = df_activites.copy()
        activites_filtrees["horaires"] = activites_filtrees["horaires"].astype(str).fillna("")
        activites_filtrees["thèmes"] = activites_filtrees["thèmes"].astype(str).fillna("")
        activites_filtrees["tarifs"] = activites_filtrees["tarifs"].replace("N/D", "0").astype(float)
        activites_filtrees = activites_filtrees[activites_filtrees["tarifs"] <= budget]
        if themes_selectionnes:
            activites_filtrees = activites_filtrees[activites_filtrees["thèmes"].apply(
                lambda x: any(theme in x for theme in themes_selectionnes))]
        activites_filtrees["note"] = activites_filtrees["note"].replace("N/D", "0").astype(float)
        activites_filtrees.loc[activites_filtrees["note"] > 10, "note"] /= 2
        activites_filtrees = activites_filtrees.sort_values(by="note", ascending=False).to_dict(orient="records")

        for item in activites_filtrees + restaurants_filtres:
            item["image"] = item.get("image", "default_image.jpg")

        events = []
        current_time = datetime.strptime(f"{debut_heure}:00", "%H:%M")
        end_time = datetime.strptime(f"{fin_heure}:00", "%H:%M")

        resto_added = 0
        act_added = 0

        used_indices = set()

        while current_time + timedelta(minutes=30) <= end_time:
            candidates = []

            # Sélection des restaurants possibles
            for i, r in enumerate(restaurants_filtres):
                if i in used_indices:
                    continue
                r_coords = get_coords(r["address"])
                if not r_coords:
                    continue
                dist = geodesic(coord_centre, r_coords).km
                # Conditions horaires midi ou soir
                if datetime.strptime("11:30", "%H:%M") <= current_time <= datetime.strptime("15:30", "%H:%M") - timedelta(hours=2):
                    candidates.append(("Restaurant", r, 120, dist, i))
                elif datetime.strptime("19:00", "%H:%M") <= current_time <= datetime.strptime("21:00", "%H:%M") - timedelta(hours=2):
                    candidates.append(("Restaurant", r, 120, dist, i))

            # Puis les activités si pas déjà assez
            if len(candidates) == 0 and act_added < nombre_activites:
                for j, a in enumerate(activites_filtrees):
                    if j in used_indices:
                        continue
                    a_coords = get_coords(a["adresse"])
                    if not a_coords:
                        continue
                    dist = geodesic(coord_centre, a_coords).km
                    candidates.append(("Activité", a, 60, dist, j))

            if not candidates:
                current_time += timedelta(minutes=15)
                continue

            # Trier par proximité
            candidates.sort(key=lambda x: x[3])  # distance

            # Choisir le meilleur élément
            for typ, item, duration, _, idx in candidates:
                prev_address = (
                    events[-1][1].get("adresse") if events and events[-1][0] != "Marche"
                    else events[-2][1].get("adresse") if len(events) >= 2 else adresse_depart
                )
                next_address = item.get("adresse") or item.get("address")
                walk_min = calculate_walking_minutes(prev_address, next_address)
                total_duration = walk_min + duration

                if current_time + timedelta(minutes=total_duration) <= end_time:
                    start_walk = current_time
                    end_walk = current_time + timedelta(minutes=walk_min)
                    start_act = end_walk
                    end_act = end_walk + timedelta(minutes=duration)

                    events.append(("Marche", {"from": prev_address, "to": next_address, "duration": walk_min}, start_walk, end_walk))
                    events.append((typ, item, start_act, end_act))
                    used_indices.add(idx)
                    current_time = end_act
                    if typ == "Restaurant":
                        resto_added += 1
                    else:
                        act_added += 1
                    break
            else:
                current_time += timedelta(minutes=15)

        planning = [{
            "titre": typ,
            "item": el,
            "debut": start.strftime("%Hh%M"),
            "fin": end.strftime("%Hh%M")
        } for typ, el, start, end in events]

        return render_template("resultats.html", planning=planning, jour_label=jour_label)


    return render_template("index.html", themes_disponibles=themes_disponibles, types_restaurants=types_restaurants)

if __name__ == "__main__":
    app.run(debug=True)
