import pandas as pd

# Chargement du fichier
df = pd.read_csv("restaurants_corriges.csv")

# Fonction pour simplifier les spécialités
def simplifier_specialite(specialties):
    if pd.isna(specialties):
        return "Autres"
    
    specialties = specialties.lower()
    
    if any(word in specialties for word in ["italien", "pizza", "pâtes"]):
        return "Italien"
    if any(word in specialties for word in ["japonais", "sushi", "ramen"]):
        return "Japonais"
    if any(word in specialties for word in ["chinois", "asiatique", "wok", "thaï", "vietnamien"]):
        return "Asiatique"
    if any(word in specialties for word in ["indien", "curry", "tandoori"]):
        return "Indien"
    if any(word in specialties for word in ["burger", "américain", "fast-food"]):
        return "Américain"
    if any(word in specialties for word in ["méditerranéen", "tapas", "grec"]):
        return "Méditerranéen"
    if any(word in specialties for word in ["végétarien", "vegan", "healthy"]):
        return "Végétarien / Vegan"
    if any(word in specialties for word in ["gastronomique", "gourmet", "cuisine créative"]):
        return "Gastronomique"
    if any(word in specialties for word in ["bistrot", "brasserie", "français"]):
        return "Français"
    if any(word in specialties for word in ["crêperie", "breton"]):
        return "Crêperie"
    
    return "Autres"

# Application de la fonction
df["categorie_specialite"] = df["specialties"].apply(simplifier_specialite)

# Sauvegarde dans un nouveau fichier CSV
df.to_csv("restaurants_avec_categories.csv", index=False)

print("✅ Fichier 'restaurants_avec_categories.csv' généré avec succès.")
