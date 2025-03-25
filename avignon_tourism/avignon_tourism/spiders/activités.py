import scrapy
import json
import re
from html import unescape

class ActivitesSpider(scrapy.Spider):
    name = "activites"
    allowed_domains = ["grandavignon-destinations.fr"]
    start_urls = [
        "https://www.grandavignon-destinations.fr/sites-a-visiter/"
    ] + [
        f"https://www.grandavignon-destinations.fr/sites-a-visiter/page/{i}/" for i in range(2, 6)
    ]

    def parse(self, response):
        """
        Scrape toutes les activités sur la page principale et extrait :
        - Nom
        - Lien vers la page de détail
        - Prix
        - Note
        - Image principale
        Puis envoie chaque activité pour extraction détaillée.
        """
        activites = response.xpath("//div[contains(@class, 'wpet-block-list__offer')]")
        if not activites:
            self.logger.warning(f"Aucune activité trouvée sur {response.url}")

        for activite in activites:
            lien = activite.xpath(".//a[contains(@class, 'stretched-link')]/@href").get()
            nom = activite.xpath(".//h2[contains(@class, 'iris-card__content__title')]/a/text()").get(default="").strip()

            prix = activite.xpath(".//div[contains(@class, 'iris-card__content__price')]//strong/text()").get()
            prix = self.extract_price(prix)

            note = activite.xpath(".//span[contains(@class, 'iris-card__label')]/text()").get()
            note = self.extract_note(note)

            # Extraire l'image principale
            image_url = activite.xpath(".//img/@src").get()  # Sélectionner l'URL de l'image
            if image_url and not image_url.startswith("http"):
                image_url = response.urljoin(image_url)  # Convertir en URL complète si nécessaire

            if lien and nom:
                self.logger.info(f"Activité trouvée: {nom} - {lien} - {prix}€ - Note: {note}/10 - Image: {image_url}")
                yield response.follow(lien, self.parse_details, meta={"nom": nom, "prix": prix, "note": note, "image": image_url})
            else:
                self.logger.warning(f"Activité ignorée (pas de lien ou de nom) sur {response.url}")

    def parse_details(self, response):
        """
        Scrape les détails d'une activité sans transformer les horaires (gérés par le pipeline).
        """
        nom = response.meta["nom"]
        prix = response.meta["prix"]
        note = response.meta["note"]
        image_url = response.meta["image"]
        
        # Extraire le script contenant les données JSON
        script_content = response.xpath("//script[contains(text(), 'IRISCollectionTheme')]/text()").get()
        
        if script_content:
            try:
                json_data = json.loads(script_content.split('var IRISCollectionTheme = ')[1].split('/*')[0].strip().rstrip(';'))
                wpet_fields = json_data.get("queriedObject", {}).get("wpetFields", {})

                themes = wpet_fields.get("themes", [])
                langues = wpet_fields.get("langues-parlees", [])
                
                adresse_parts = [
                    wpet_fields.get("adresse-1", ""),
                    wpet_fields.get("commune", ""),
                    wpet_fields.get("code-postal", "")
                ]
                adresse = ", ".join([part for part in adresse_parts if part])

            except Exception as e:
                self.logger.error(f"Erreur JSON sur {response.url}: {e}")
                themes, langues, adresse = [], [], ""
        else:
            themes, langues, adresse = [], [], ""

        # Téléphone
        telephone = response.xpath("//a[contains(@href, 'tel:')]/text()").get(default="").strip()
        telephone = self.clean_telephone(telephone)

        # **Extraire les horaires bruts (pipeline les formate)**
        horaires_bruts = []
        horaires_rows = response.xpath("//div[@id='table-periodes']//table//tbody//tr")
        for row in horaires_rows:
            jour = row.xpath("./th/text()").get()
            heure = row.xpath("./td/text()").get()
            if jour and heure:
                horaires_bruts.append(f"{jour}: {heure}")

        horaires_final = "; ".join(horaires_bruts) if horaires_bruts else "Non disponible"

        yield {
            "nom": nom,
            "thèmes": ", ".join(themes),
            "langues": ", ".join(langues),
            "adresse": adresse,
            "tel": telephone,
            "tarifs": prix,
            "note": note,
            "horaires": horaires_final,  # **Laisse le pipeline transformer ces données**
            "image": image_url  # Image principale de l'activité
        }

    def extract_price(self, price_text):
        """
        Extrait le prix sous forme de float. Retourne 0.0 si "Gratuit".
        """
        if not price_text:
            return "N/D"
        
        price_text = unescape(price_text).strip()
        
        if "Gratuit" in price_text:
            return "0.0"
        
        match = re.search(r"(\d+[.,]?\d*)", price_text)
        return match.group(1).replace(",", ".") if match else "N/D"

    def extract_note(self, note_text):
        """
        Extrait la note sous forme de float. Retourne "N/D" si non disponible.
        """
        if not note_text:
            return "N/D"

        match = re.search(r"(\d+[.,]?\d*)", note_text)
        return match.group(1).replace(",", ".") if match else "N/D"

    def clean_telephone(self, phone):
        """
        Nettoie le format des numéros de téléphone.
        """
        if not phone:
            return "N/D"
        
        phone = re.sub(r"[^\d+]", "", phone)  # Supprime tout sauf chiffres et "+"
        return phone if phone.startswith("+") else f"+33{phone[1:]}" if phone.startswith("0") else phone
