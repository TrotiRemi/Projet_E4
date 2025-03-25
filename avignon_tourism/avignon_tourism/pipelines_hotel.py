import re

class HotelPipeline:
    def process_item(self, item, spider):
        # ✅ 1️⃣ Transformer la colonne "equipements" en une liste propre
        if "equipements" in item and isinstance(item["equipements"], str):
            item["equipements"] = item["equipements"].split(" | ")

        # ✅ 2️⃣ Extraire et formater correctement les prix
        if "price" in item and isinstance(item["price"], str):
            prix_list = self.extract_prices(item["price"])

            # Vérification et application du format "€"
            item["prix_min"] = f"{min(prix_list)}€" if prix_list else "0€"
            item["prix_max"] = f"{max(prix_list)}€" if prix_list else "0€"

        return item

    def extract_prices(self, price_text):
        """ Extrait tous les prix valides sous forme de nombres et retourne une liste d'entiers """
        # ✅ Extraction de tous les nombres dans la chaîne
        prices = re.findall(r'(\d+)\s*€?', price_text)  # Capture les nombres avec ou sans "€"
        
        # ✅ Filtrage des nombres valides
        valid_prices = [int(price) for price in prices if price.isdigit() and int(price) > 0]

        return valid_prices
