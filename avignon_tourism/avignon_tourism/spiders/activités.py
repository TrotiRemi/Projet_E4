import scrapy

class ActivitesSpider(scrapy.Spider):
    name = "activites"
    allowed_domains = ["grandavignon-destinations.fr"]
    start_urls = [
        "https://www.grandavignon-destinations.fr/sites-a-visiter/"
    ] + [
        f"https://www.grandavignon-destinations.fr/sites-a-visiter/page/{i}/" for i in range(2, 6)
    ]

    def parse(self, response):
        """Extrait les liens des activités et les suit pour récupérer les détails."""
        for activite in response.xpath("//div[contains(@class, 'wpet-block-list__offer')]"):
            lien = activite.xpath(".//a[contains(@class, 'stretched-link')]/@href").get()
            if lien:
                yield response.follow(lien, self.parse_details)

    def parse_details(self, response):
        """Extrait les détails de chaque activité, y compris les tarifs, horaires, moyens de paiement, et la note."""
        tarifs = []
        rows = response.xpath("//div[@id='table-tarifs']//table//tbody//tr")

        self.logger.debug(f"Nombre de lignes dans le tableau des tarifs pour {response.url}: {len(rows)}")

        for row in rows:
            description = row.xpath("./th[@class='wpet-table__cell']//text()").getall()
            prix_min = row.xpath("./td[@class='wpet-table__cell'][1]//text()").getall()
            prix_max = row.xpath("./td[@class='wpet-table__cell'][2]//text()").getall()

            # Nettoyage des données
            description = " ".join([text.strip() for text in description if text.strip()])
            prix_min = " ".join([text.strip() for text in prix_min if text.strip()])
            prix_max = " ".join([text.strip() for text in prix_max if text.strip()])

            if description and prix_min:
                if prix_max and prix_max not in ["–", "Non communiqué"]:
                    tarifs.append({"description": description, "prix": f"{prix_min} - {prix_max}"})
                else:
                    tarifs.append({"description": description, "prix": prix_min})

        # Extraction du nom, adresse et note
        nom = response.xpath("//h1[contains(@class, 'wpet-offer-name')]/text()").get(default="").strip()
        adresse = response.xpath("//div[contains(@class, 'wpet-address__datas__content')]/text()").get(default="").strip()

        # Extraction de la note (si présente)
        note = response.xpath("//span[contains(@class, 'iris-card__label')]/text()").get(default="Non disponible").strip()

        # Extraction des horaires d'ouverture
        horaires = []
        horaires_rows = response.xpath("//div[@id='table-periodes']//table//tbody//tr")
        for row in horaires_rows:
            jour = row.xpath("./th[@class='wpet-table__cell']//text()").get()
            heure = row.xpath("./td[@class='wpet-table__cell']//text()").get()
            if jour and heure:
                horaires.append(f"{jour}: {heure}")

        # Extraction des moyens de paiement
        moyens_paiement = response.xpath("//div[contains(@class, 'wpet-list-tags')]//li/text()").getall()
        moyens_paiement = [paiement.strip() for paiement in moyens_paiement if paiement.strip()]

        self.logger.debug(f"Tarifs récupérés pour {nom}: {tarifs}")
        self.logger.debug(f"Note récupérée pour {nom}: {note}")

        yield {
            "nom": nom,
            "adresse": adresse,
            "note": note,  # Ajout de la note
            "tarifs": "; ".join([f"{t['description']}: {t['prix']}" for t in tarifs]) if tarifs else "Aucun tarif disponible",
            "horaires": "; ".join(horaires) if horaires else "Non disponible",
            "moyens_paiement": "; ".join(moyens_paiement) if moyens_paiement else "Non précisé",
        }
