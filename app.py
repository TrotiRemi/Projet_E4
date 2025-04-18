from flask import Flask, render_template, request, redirect, flash 
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "votre_clé_secrète"

adresse_depart = "Casa Bronzini"
df_activites = pd.read_csv("activites.csv")
df_restaurants = pd.read_csv("restaurants.csv")
df_enriched = pd.read_csv("matrice_distances_enrichie.csv")

MAX_WALK_MINUTES = 30
df_enriched = df_enriched[df_enriched["time_min"] <= MAX_WALK_MINUTES]

distance_lookup = df_enriched.set_index(["from_name", "to_name"])["time_min"].to_dict()
address_lookup = df_enriched.set_index("from_name")["from_address"].to_dict()
address_lookup.update(df_enriched.set_index("to_name")["to_address"].to_dict())

all_names = set(df_enriched["from_name"]) | set(df_enriched["to_name"])
df_valid_activites = df_activites[df_activites["nom"].isin(all_names)]
name_to_activite = {row["nom"]: row for _, row in df_valid_activites.iterrows()}
df_valid_restos = df_restaurants[df_restaurants["name"].isin(all_names)]
name_to_restaurant = {row["name"]: row for _, row in df_valid_restos.iterrows()}

themes_disponibles = sorted(set(theme.strip() for t in df_activites["catégorie_simplifiée"].dropna() for theme in t.split(", ")))
types_restaurants = sorted(set(s.strip() for t in df_restaurants["categorie_specialite"].dropna() for s in t.split(",")))

rythme_config = {
    "intensif": {"midi": (12, 12.75), "soir": (20, 21), "nb_act": (3, 8)},
    "complet": {"midi": (11.75, 13), "soir": (20, 21.25), "nb_act": (2, 6)},
    "normal": {"midi": (11.75, 13.25), "soir": (19.75, 21.25), "nb_act": (2, 5)},
    "calme": {"midi": (11.5, 13.25), "soir": (19.75, 21.75), "nb_act": (1, 4)},
    "tres_calme": {"midi": (11.5, 13.5), "soir": (19.5, 22), "nb_act": (0, 3)}
}

def get_min_price(pricing_str):
    try:
        if not isinstance(pricing_str, str): return None
        prixs = [float(p.replace("\u20ac", "").replace(",", ".").strip()) for p in pricing_str.split(",") if p.strip()]
        return min(prixs) if prixs else None
    except: return None

def nettoyer_note(note):
    try:
        if note == "N/D" or pd.isna(note):
            return None
        note = float(str(note).replace(",", ".").strip())
        if note > 10:
            note /= 2
        return round(note, 1)
    except:
        return None

def nettoyer_horaires(horaire):
    if isinstance(horaire, str) and horaire.strip().lower() == "n/d":
        return "Ouvert tout le temps"
    return horaire

def parse_int(val, default):
    try: return int(val)
    except: return default

def parse_float(val, default):
    try: return float(val)
    except: return default

def jour_to_label(abbr):
    return {
        "L": "Lundi",
        "M": "Mardi",
        "ME": "Mercredi",
        "J": "Jeudi",
        "V": "Vendredi",
        "S": "Samedi",
        "D": "Dimanche"
    }.get(abbr, "Lundi")

def heure_float_to_datetime(base_date, h):
    heures = int(h)
    minutes = int((h - heures) * 60)
    return datetime(base_date.year, base_date.month, base_date.day, heures, minutes)

def get_precomputed_walking_minutes(from_name, to_name):
    from_name, to_name = from_name.strip().lower(), to_name.strip().lower()
    for a, b in [(from_name, to_name), (to_name, from_name)]:
        for key in distance_lookup:
            if key[0].strip().lower() == a and key[1].strip().lower() == b:
                return distance_lookup[key]
    return None

def place_activites_between(start_time, end_time, start_place, end_place, activites, planning, used, nb_activites_voulues):
    base_date = datetime.today()

    if nb_activites_voulues <= 0:
        return

    position = start_place
    current_time = start_time

    # Temps total disponible sans toucher end_time
    duree_dispo_total = (end_time - start_time).total_seconds() / 60  # en minutes

    candidats = [act for act in activites if act["nom"] not in used]

    for i in range(nb_activites_voulues):
        if not candidats:
            break

        # Chercher activité la plus proche
        candidats.sort(key=lambda act: get_precomputed_walking_minutes(position, act["nom"]) or 9999)
        act = candidats.pop(0)

        # Temps de marche vers cette activité
        walk_to_act = get_precomputed_walking_minutes(position, act["nom"])
        if walk_to_act is None or walk_to_act > MAX_WALK_MINUTES:
            continue

        # Temps de marche de cette activité vers end_place (ex : resto)
        walk_to_end = get_precomputed_walking_minutes(act["nom"], end_place)
        if walk_to_end is None:
            walk_to_end = 0

        # ➡️ Temps restant après la marche actuelle et la marche vers la fin
        duree_restante = (end_time - current_time).total_seconds() / 60 - walk_to_act - walk_to_end

        if duree_restante <= 0:
            break

        # Répartir également la durée restante sur les activités restantes
        duree_actuelle = duree_restante / (nb_activites_voulues - i)

        # Avancer : marche -> activité
        arrive = current_time + timedelta(minutes=walk_to_act)
        fin = arrive + timedelta(minutes=duree_actuelle)

        planning.append({
            "titre": "Marche",
            "item": {"from": address_lookup.get(position), "to": address_lookup.get(act["nom"]), "duration": walk_to_act},
            "debut": current_time,
            "fin": arrive
        })
        planning.append({
            "titre": "Activité",
            "item": act,
            "debut": arrive,
            "fin": fin
        })

        used.add(act["nom"])
        position = act["nom"]
        current_time = fin

    # ➡️ Enfin, après les activités ➔ marche vers end_place
    if position != end_place:
        walk_final = get_precomputed_walking_minutes(position, end_place)
        if walk_final is not None and walk_final <= MAX_WALK_MINUTES:
            arrive_end = current_time
            fin_end = arrive_end + timedelta(minutes=walk_final)
            planning.append({
                "titre": "Marche",
                "item": {"from": address_lookup.get(position), "to": address_lookup.get(end_place), "duration": walk_final},
                "debut": arrive_end,
                "fin": fin_end
            })


def trouver_restaurants(restaurants_list, start_point, max_walk_minutes=60):
    candidats = []
    for resto1 in restaurants_list:
        walk1 = get_precomputed_walking_minutes(start_point, resto1["name"])
        if walk1 is None:
            print(f"[DEBUG] Distance manquante: {start_point} ➔ {resto1['name']}")
            continue
        if walk1 > max_walk_minutes:
            continue

        for resto2 in restaurants_list:
            if resto1["name"] == resto2["name"]:
                continue
            walk2 = get_precomputed_walking_minutes(start_point, resto2["name"])
            walk_between = get_precomputed_walking_minutes(resto1["name"], resto2["name"])

            if walk2 is None:
                print(f"[DEBUG] Distance manquante: {start_point} ➔ {resto2['name']}")
                continue
            if walk2 > max_walk_minutes:
                continue
            if walk_between is None:
                print(f"[DEBUG] Distance manquante: {resto1['name']} ➔ {resto2['name']}")
                continue
            if walk_between > max_walk_minutes:
                continue

            note_moyenne = (resto1["rating"] + resto2["rating"]) / 2
            candidats.append((note_moyenne, resto1, resto2))

    if not candidats:
        return None, None

    meilleurs = sorted(candidats, key=lambda x: -x[0])[0]
    return meilleurs[1], meilleurs[2]


def planifier_journee(debut_heure, fin_heure, rythme, activites, restaurants_list, resto_midi, resto_soir):
    base_date = datetime.today()
    planning = []
    used = set()
    position = adresse_depart

    start_day = datetime(base_date.year, base_date.month, base_date.day, debut_heure)
    end_day = datetime(base_date.year, base_date.month, base_date.day, fin_heure)

    cfg = rythme_config[rythme]
    nb_activites_matin = cfg["nb_act"][0]
    nb_activites_aprem = cfg["nb_act"][1]
    midi_start = heure_float_to_datetime(base_date, cfg["midi"][0])
    midi_end = heure_float_to_datetime(base_date, cfg["midi"][1])
    soir_start = heure_float_to_datetime(base_date, cfg["soir"][0])
    soir_end = heure_float_to_datetime(base_date, cfg["soir"][1])

    resto_midi_obj = None
    resto_soir_obj = None

    if resto_midi or resto_soir:
        resto_midi_obj, resto_soir_obj = trouver_restaurants(restaurants_list, adresse_depart)

    # Si l'utilisateur a coché un resto mais aucun trouvé, alors on arrête
    if resto_midi and not resto_midi_obj:
        print("[DEBUG] Aucun restaurant midi trouvé")
        return []
    if resto_soir and not resto_soir_obj:
        print("[DEBUG] Aucun restaurant soir trouvé")
        return []

    if resto_midi and resto_midi_obj:
        used.add(resto_midi_obj["name"])
    if resto_soir and resto_soir_obj:
        used.add(resto_soir_obj["name"])

    # Déterminer les moments de la journée
    moments = []
    total_activites = nb_activites_matin + nb_activites_aprem

    if resto_midi and resto_soir:
        # Cas normal : resto midi ET soir
        moments.append((start_day, midi_start, adresse_depart, resto_midi_obj["name"], nb_activites_matin))
        moments.append((midi_end, soir_start, resto_midi_obj["name"], resto_soir_obj["name"], nb_activites_aprem))
        moments.append((soir_end, end_day, resto_soir_obj["name"], adresse_depart, 0))
    elif resto_midi and not resto_soir:
        # Seulement resto midi
        moments.append((start_day, midi_start, adresse_depart, resto_midi_obj["name"], nb_activites_matin))
        moments.append((midi_end, end_day, resto_midi_obj["name"], adresse_depart, nb_activites_aprem))
    elif not resto_midi and resto_soir:
        # Seulement resto soir
        moments.append((start_day, soir_start, adresse_depart, resto_soir_obj["name"], total_activites))
        moments.append((soir_end, end_day, resto_soir_obj["name"], adresse_depart, 0))
    else:
        # Aucun resto (ni midi ni soir)
        moments.append((start_day, end_day, adresse_depart, adresse_depart, total_activites))

    # Placer les activités
    for start_time, end_time, start_place, end_place, nb_acts in moments:
        place_activites_between(start_time, end_time, start_place, end_place, activites, planning, used, nb_acts)

    # Ajouter les restaurants si demandés
    if resto_midi and resto_midi_obj:
        planning.append({"titre": "Restaurant", "item": resto_midi_obj, "debut": midi_start, "fin": midi_end})
    if resto_soir and resto_soir_obj:
        planning.append({"titre": "Restaurant", "item": resto_soir_obj, "debut": soir_start, "fin": soir_end})

    planning.sort(key=lambda x: x["debut"])

    return planning



@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        participants = parse_int(request.form.get("participants"), 1)
        jour_label = jour_to_label(request.form.get("jour", ""))
        debut_heure = parse_int(request.form.get("debut_heure"), 9)
        fin_heure = parse_int(request.form.get("fin_heure"), 23)
        budget = parse_float(request.form.get("budget"), 0)
        rythme = request.form.get("rythme", "normal").lower()
        resto_midi = "midi" in request.form.getlist("repas")
        resto_soir = "soir" in request.form.getlist("repas")
        themes_selectionnes = request.form.getlist("themes")
        types_selectionnes = request.form.getlist("types_restaurants")

        restaurants = df_restaurants.copy()
        restaurants["prix_min"] = restaurants["pricing"].apply(get_min_price)

        restaurants["note_corrigee"] = restaurants["rating"].apply(nettoyer_note)
        restaurants = restaurants[restaurants["note_corrigee"].notnull()]  # Garder seulement ceux avec une note valide

        restaurants = restaurants[
            (restaurants["prix_min"] * participants <= budget) &
            (restaurants[jour_label].str.lower() != "fermé")
        ]

        if types_selectionnes:
            restaurants = restaurants[
                restaurants["categorie_specialite"].apply(lambda x: any(t in x for t in types_selectionnes if isinstance(x, str)))
            ]

        if not restaurants.empty and "note_corrigee" in restaurants.columns:
            restaurants = restaurants.sort_values(by="note_corrigee", ascending=False)
            restaurants_list = restaurants.to_dict(orient="records")
        else:
            restaurants_list = []


        activites = df_activites.copy()
        activites["tarifs"] = activites["tarifs"].replace("N/D", "0").astype(float)

        # Correction PROPRE des notes avec fonction existante
        activites["note_corrigee"] = activites["note"].apply(nettoyer_note)

        # Garder uniquement celles respectant le budget
        activites = activites[activites["tarifs"] <= budget]

        # Appliquer les filtres par thèmes s'il y en a
        if themes_selectionnes:
            activites = activites[
                activites["catégorie_simplifiée"].apply(lambda x: isinstance(x, str) and any(t in x for t in themes_selectionnes))
            ]

        for col in ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]:
            if col in activites.columns:
                activites[col] = activites[col].apply(nettoyer_horaires)

        # Trier par note corrigée (les activités sans note seront en bas)
        activites = activites.sort_values(
            by="note_corrigee", ascending=False, na_position='last'
        ).to_dict(orient="records")

        planning = planifier_journee(debut_heure, fin_heure, rythme, activites, restaurants_list, resto_midi, resto_soir)

        total_marche = 0
        total_prix = 0
        nb_activites = 0
        nb_restaurants = 0

        for ev in planning:
            if ev["titre"] == "Marche":
                total_marche += ev["item"]["duration"]
            elif ev["titre"] == "Activité":
                nb_activites += 1
                if "tarifs" in ev["item"]:
                    total_prix += float(ev["item"]["tarifs"]) * participants
            elif ev["titre"] == "Restaurant":
                nb_restaurants += 1
                if "prix_min" in ev["item"]:
                    total_prix += float(ev["item"]["prix_min"]) * participants

        return render_template(
            "resultats.html",
            planning=[{
                "titre": ev["titre"],
                "item": ev["item"].to_dict() if hasattr(ev["item"], "to_dict") else ev["item"],
                "debut": ev["debut"].strftime("%Hh%M"),
                "fin": ev["fin"].strftime("%Hh%M")
            } for ev in planning],
            jour_label=jour_label,
            total_marche=total_marche,
            total_prix=round(total_prix, 2),
            nb_activites=nb_activites,
            nb_restaurants=nb_restaurants,
            participants=participants
        )

    return render_template("index.html", themes_disponibles=themes_disponibles, types_restaurants=types_restaurants)

if __name__ == "__main__":
    app.run(debug=True)