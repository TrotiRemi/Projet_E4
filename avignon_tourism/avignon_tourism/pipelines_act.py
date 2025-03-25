import re
from html import unescape

class FormatDataPipeline:
    def process_item(self, item, spider):
        """
        Nettoie et reformate les horaires et les langues.
        """
        item["horaires"] = self.format_horaires(item.get("horaires", "N/D"))
        item["langues"] = self.format_langues(item.get("langues", "N/D"))
        return item

    def format_horaires(self, horaires_str):
        """
        Convertit les horaires en un format structuré sous forme de tableau avec abréviations et gestion des plages horaires.
        Supprime les horaires inutiles (ex: 09h00-19h00 et 10h00-17h00 devient 09h00-19h00).
        """

        if not horaires_str or horaires_str == "Non disponible":
            return "Non disponible"

        # Remplacement des entités HTML (&agrave; → à, etc.)
        horaires_str = unescape(horaires_str)

        # Correspondance des jours avec leurs abréviations
        jours_abbr = {
            "Lundi": "L",
            "Mardi": "M",
            "Mercredi": "ME",
            "Jeudi": "J",
            "Vendredi": "V",
            "Samedi": "S",
            "Dimanche": "D"
        }

        horaires_dict = {}

        # Expression régulière pour capturer les horaires
        horaires_pattern = re.findall(r"(\w+): Ouvert de (\d{1,2})h à (\d{1,2})h", horaires_str)

        for jour, debut, fin in horaires_pattern:
            abbr = jours_abbr.get(jour, jour[:2])  # Utilise l'abréviation ou les 2 premières lettres
            debut = int(debut)  # Convertir en entier pour comparaison
            fin = int(fin)

            if abbr not in horaires_dict:
                horaires_dict[abbr] = []

            horaires_dict[abbr].append((debut, fin))  # Stocke les plages horaires en tuples

        # Suppression des répétitions et fusion des horaires corrects
        horaires_final = []
        for abbr in sorted(horaires_dict.keys()):
            horaires_list = sorted(horaires_dict[abbr])  # Trie par heure de début

            # Suppression des horaires inutiles (ex: 09h00-19h00 et 10h00-17h00 → 09h00-19h00)
            filtered_horaires = []
            for i, (start, end) in enumerate(horaires_list):
                if not filtered_horaires or start > filtered_horaires[-1][1]:  
                    # Ajoute seulement si le nouvel horaire ne se trouve pas déjà dans l'ancien
                    filtered_horaires.append((start, end))

            # Formater proprement
            horaires_format = [f"{h[0]:02d}h00-{h[1]:02d}h00" for h in filtered_horaires]
            horaires_final.append(f"{abbr}: {' et '.join(horaires_format)}")

        return "; ".join(horaires_final)

    def format_langues(self, langues_str):
        """
        Convertit la liste des langues en abréviations (ex: "Français, Anglais" → "Fr, En").
        """

        # Dictionnaire des abréviations
        langues_abbr = {
            "Français": "Fr",
            "Anglais": "En",
            "Allemand": "De",
            "Espagnol": "Es",
            "Italien": "It",
            "Chinois": "Zh",
            "Japonais": "Ja",
            "Russe": "Ru",
            "Portugais": "Pt",
            "Polonais": "Pl",
            "Néerlandais": "Nl",
            "Arabe": "Ar"
        }

        # Vérifie si c'est une liste ou une chaîne
        if isinstance(langues_str, list):
            langues = [langues_abbr.get(lang.strip(), lang.strip()) for lang in langues_str]
        elif isinstance(langues_str, str):
            langues = [langues_abbr.get(lang.strip(), lang.strip()) for lang in langues_str.split(",")]
        else:
            return ""

        return ", ".join(langues)

