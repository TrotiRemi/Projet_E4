import pandas as pd

# Charger les fichiers CSV
hotel_df = pd.read_csv("hotel.csv")
bar_df = pd.read_csv("bar.csv")
restaurant_df = pd.read_csv("restaurant.csv")
animation_df = pd.read_csv("animation.csv")

# Ajouter une colonne "type" pour identifier chaque catégorie
hotel_df["type"] = "hotel"
bar_df["type"] = "bar"
restaurant_df["type"] = "restaurant"
animation_df["type"] = "animation"

# Normalisation des colonnes communes
hotel_df = hotel_df.rename(columns={"nom": "nom", "adresse": "adresse", "note": "note", "prix_min": "tarif", "prix_max": "tarif_max"})
bar_df = bar_df.rename(columns={"nom": "nom", "adresse": "adresse", "note": "note", "prix_mini": "tarif"})
restaurant_df = restaurant_df.rename(columns={"nom": "nom", "adresse": "adresse", "note": "note", "prix_min": "tarif"})
animation_df = animation_df.rename(columns={"nom": "nom", "adresse": "adresse", "note": "note", "tarifs": "tarif"})

# Sélection des colonnes pertinentes
columns = ["nom", "adresse", "note", "tarif", "type"]
hotel_df = hotel_df[columns]
bar_df = bar_df[columns]
restaurant_df = restaurant_df[columns]
animation_df = animation_df[columns]

# Fusionner les fichiers en un seul
activite_df = pd.concat([hotel_df, bar_df, restaurant_df, animation_df], ignore_index=True)

# Sauvegarde dans un nouveau fichier CSV
activite_df.to_csv("activite.csv", index=False)
print("Fichier activite.csv généré avec succès !")

# Générer un script SQL pour insérer les données
sql_script = """
CREATE TABLE Activite (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(255),
    adresse TEXT,
    note FLOAT,
    tarif FLOAT,
    type VARCHAR(50)
);

LOAD DATA INFILE 'activite.csv'
INTO TABLE Activite
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(nom, adresse, note, tarif, type);
"""

# Sauvegarde du script SQL dans un fichier
with open("import_data.sql", "w", encoding="utf-8") as file:
    file.write(sql_script)

print("Script SQL 'import_data.sql' généré avec succès !")
