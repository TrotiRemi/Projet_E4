from flask import Flask, render_template, request, redirect, flash
import pandas as pd

app = Flask(__name__)
app.secret_key = "votre_clé_secrète"

# Chargement des données
df_activites = pd.read_csv("activite.csv")
df_restaurants = pd.read_csv("restaurants.csv")

def extraire_horaire_du_jour(horaires_str, jour_abbr):
    if not isinstance(horaires_str, str):
        return "Fermé"
    horaires = horaires_str.split(";")
    for bloc in horaires:
        bloc = bloc.strip()
        if bloc.startswith(f"{jour_abbr}:"):
            try:
                return bloc.split(":", 1)[1].strip()
            except:
                return "Fermé"
    return "Fermé"

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

# Prétraitement
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
        debut_heure = int(debut_heure) if debut_heure else None
        fin_heure = int(fin_heure) if fin_heure else None

        resultats_final = []

        jour_abbr_map = {
            "Lundi": "L", "Mardi": "M", "Mercredi": "ME",
            "Jeudi": "J", "Vendredi": "V", "Samedi": "S", "Dimanche": "D"
        }
        jour_abbr = jour_abbr_map.get(jour_label, "L")

        # Restaurants
        restaurants_filtres = df_restaurants.copy()
        restaurants_filtres["rating"] = restaurants_filtres["rating"].replace("N/D", "0").astype(float)
        restaurants_filtres.loc[restaurants_filtres["rating"] > 10, "rating"] = 0
        restaurants_filtres = restaurants_filtres[restaurants_filtres["prix_min"] <= budget]
        restaurants_filtres = restaurants_filtres[restaurants_filtres[jour_label].str.lower() != "fermé"]
        if types_selectionnes:
            restaurants_filtres = restaurants_filtres[restaurants_filtres["specialties"].apply(
                lambda x: any(t in x for t in types_selectionnes if isinstance(x, str)))]
        restaurants_filtres = restaurants_filtres.sort_values(by="rating", ascending=False)
        restaurants_filtres = restaurants_filtres.head(nombre_restaurants).to_dict(orient="records")

        # Activités
        activites_filtrees = df_activites.copy()
        activites_filtrees["horaires"] = activites_filtrees["horaires"].astype(str).fillna("")
        activites_filtrees["thèmes"] = activites_filtrees["thèmes"].astype(str).fillna("")
        if jour and (not debut_heure or not fin_heure):
            activites_filtrees = activites_filtrees[
                activites_filtrees["horaires"].str.contains(jour, na=False) |
                activites_filtrees["horaires"].str.contains("Non disponible", na=False)
            ]
        if debut_heure and fin_heure:
            def check_time_available(horaires):
                if "Non disponible" in horaires:
                    return True
                for horaire in horaires.split("; "):
                    try:
                        jour_code, plage = horaire.split(": ")
                        plages_horaires = plage.split(" et ")
                        for plage in plages_horaires:
                            h_debut, h_fin = map(int, plage.replace("h00", "").split("-"))
                            if debut_heure <= h_fin and fin_heure >= h_debut:
                                return True
                    except ValueError:
                        pass
                return False
            activites_filtrees = activites_filtrees[activites_filtrees["horaires"].apply(check_time_available)]
        activites_filtrees["tarifs"] = activites_filtrees["tarifs"].replace("N/D", "0").astype(float)
        activites_filtrees = activites_filtrees[activites_filtrees["tarifs"] <= budget]
        if themes_selectionnes:
            activites_filtrees = activites_filtrees[activites_filtrees["thèmes"].apply(
                lambda x: any(theme in x for theme in themes_selectionnes))]
        activites_filtrees["note"] = activites_filtrees["note"].replace("N/D", "0").astype(float)
        activites_filtrees.loc[activites_filtrees["note"] > 10, "note"] /= 2
        activites_filtrees = activites_filtrees.sort_values(by="note", ascending=False)
        activites_filtrees = activites_filtrees.head(nombre_activites).to_dict(orient="records")

        for activite in activites_filtrees:
            activite["image"] = activite.get("image", "default_image.jpg")

        resultats_final.extend(restaurants_filtres)
        resultats_final.extend(activites_filtrees)

        for item in resultats_final:
            if "horaires" in item:
                item["horaire_du_jour"] = extraire_horaire_du_jour(item["horaires"], jour_abbr)
            elif jour_label in item:
                item["horaire_du_jour"] = item[jour_label]
            else:
                item["horaire_du_jour"] = "Fermé"

        return render_template("resultats.html", activites=resultats_final, jour_label=jour_label)

    return render_template("index.html", themes_disponibles=themes_disponibles, types_restaurants=types_restaurants)

if __name__ == "__main__":
    app.run(debug=True)
