import re

class CleanRestaurantPipeline:
    def transform_opening_hours(self, item):
        jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        horaires_dict = {jour: "Fermé" for jour in jours_semaine}

        if "opening_hours" in item and isinstance(item["opening_hours"], list):
            for horaire in item["opening_hours"]:
                match = re.match(r"(\w+):\s*Ouvert(?: de (\d{1,2}h\d{0,2}) à (\d{1,2}h\d{0,2}))?", horaire)
                if match:
                    jour, heure_debut, heure_fin = match.groups()
                    if jour in jours_semaine:
                        if heure_debut and heure_fin:
                            horaires_dict[jour] = f"{heure_debut} - {heure_fin}"
                        else:
                            horaires_dict[jour] = "09h00 - 23h00"  # Par défaut si aucune heure précise n'est fournie

        # Mettre à jour l'item avec les nouveaux horaires
        item.update(horaires_dict)

        # Supprimer la colonne d'origine
        item.pop("opening_hours", None)

        return item  # Retourne l'item mis à jour
    
    LANGUAGES_MAP = {
        "Français": "FR",
        "Anglais": "EN",
        "Italien": "IT",
        "Espagnol": "ES",
        "Allemand": "DE",
        "Néerlandais": "NL",
        "Chinois": "ZH",
        "Japonais": "JA",
        "Russe": "RU",
        "Portugais": "PT",
        "Danois": "DA"
    }
    
    SPECIALTY_MAP = {
        "Cuisine végétalienne": "végétalienne",
        "Plats végétariens": "végétariens",
        "Cuisine bio": "bio",
        "Cuisine méditerranéenne": "méditerranéenne",
        "Cuisine traditionnelle française": "française",
        "Cuisine Provençale": "provençale",
        "Plats sans gluten": "sans gluten",
        "Plats sans lactose": "sans lactose",
        "Propose des plats \"fait maison\"": "fait maison",
        "Cuisine italienne": "italienne",
        "Poisson": "poisson",
        "Saladerie": "saladerie",
        "Cuisine gastronomique": "gastronomique",
        "Cuisine halal": "halal",
        "Cuisine nord-américaine": "nord-américaine",
        "Cuisine orientale": "orientale",
        "Cuisine espagnole": "espagnole",
        "Cuisine Europe de l'Est": "Europe de l'Est",
        "Spécial viande": "viande"
    }

    def process_item(self, item, spider):
        # Nettoyer le rating (garder uniquement le nombre)
        rating = item.get("rating", "").strip()
        match = re.search(r"(\d+(\.\d+)?)", rating)  # Cherche un nombre (ex: 8.9)
        item["rating"] = float(match.group(1)) if match else 0  # Convertit en float, sinon 0

        # Nettoyer le numéro de téléphone (enlever 'tel:')
        phone = item.get("phone", "")
        item["phone"] = phone.replace("tel:", "").strip() if phone else ""

        # Transformer capacity en 4 colonnes distinctes
        capacity_text = item.get("capacity", [])
        capacity_values = {
            "Nombre maximum de couverts": 0,
            "Nombre de salle(s)": 0,
            "Nombre de salles climatisée(s)": 0,
            "Nombre de couverts en terrasse": 0
        }

        # Parcourir chaque ligne de la capacité et extraire les valeurs
        for cap in capacity_text:
            for key in capacity_values.keys():
                if key in cap:
                    numbers = re.findall(r"\d+", cap)  # Récupère uniquement les nombres
                    if numbers:
                        capacity_values[key] = int(numbers[0])  # Prend la première valeur trouvée

        # Ajouter les nouvelles colonnes dans l'item
        item["couvert_max"] = capacity_values["Nombre maximum de couverts"]
        item["nombre_salle"] = capacity_values["Nombre de salle(s)"]
        item["nombre_salle_clim"] = capacity_values["Nombre de salles climatisée(s)"]
        item["couvert_terrasse"] = capacity_values["Nombre de couverts en terrasse"]

        # Supprimer l'ancienne colonne capacity
        del item["capacity"]

        raw_languages = item.get("languages", "").strip()
        if raw_languages.startswith("Nous parlons :"):
            raw_languages = raw_languages.replace("Nous parlons :", "").strip()

        languages_list = [lang.strip() for lang in raw_languages.split(",")]
        reduced_languages = [self.LANGUAGES_MAP.get(lang, lang) for lang in languages_list]

        item["languages"] = ", ".join(reduced_languages) if reduced_languages else "Non spécifié"

        # Nettoyer les spécialités
        raw_specialties = item.get("specialties", [])
        if isinstance(raw_specialties, str):
            raw_specialties = [spec.strip() for spec in raw_specialties.split(",")]

        reduced_specialties = [self.SPECIALTY_MAP.get(spec, spec) for spec in raw_specialties]
        item["specialties"] = ", ".join(reduced_specialties) if reduced_specialties else "Non spécifié"

        # Correction ici : on stocke la sortie de transform_opening_hours(item)
        item = self.transform_opening_hours(item)

        return item
