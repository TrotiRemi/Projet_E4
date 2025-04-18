import pandas as pd

# Charger ton fichier
df = pd.read_csv("activite_corrigees.csv")

# Dictionnaire de correspondance des thèmes
regroupement_themes = {
    "Art & Culture": ["Art moderne / contemporain", "Arts décoratifs", "Arts et culture", "Beaux Arts"],
    "Patrimoine Historique": [
        "Abbaye", "Château", "Château fort", "Palais", "Hôtel particulier",
        "Rempart", "Fontaine", "Place", "Tour", "Beffroi / Tour de l'horloge",
        "Clocher", "Ouvrage d'art", "Lavoir"
    ],
    "Patrimoine Religieux": ["Eglise", "Chapelle", "Monastère", "Chartreuse", "Synagogue", "Site religieux", "Collégiale"],
    "Nature & Jardins": ["Jardin", "Jardin botanique", "Jardin d'agrément", "Verger", "Parc"],
    "Sciences & Techniques": ["Sciences et techniques", "Sciences naturelles"],
    "Archéologie & Histoire": ["Archéologie", "Histoire", "Métiers"]
}

# Fonction pour trouver la catégorie simplifiée
def trouver_categorie(theme_str):
    if pd.isna(theme_str):
        return "Autres"
    themes = [t.strip() for t in theme_str.split(",")]
    for theme in themes:
        for cat, liste_themes in regroupement_themes.items():
            if theme in liste_themes:
                return cat
    return "Autres"

# Appliquer la fonction
df["catégorie_simplifiée"] = df["thèmes"].apply(trouver_categorie)

# Sauvegarder le nouveau fichier
df.to_csv("activites.csv", index=False)

print("Fichier 'activite_rassemble.csv' généré avec succès !")