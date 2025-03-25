import scrapy
import os

class HotelSpider(scrapy.Spider):
    name = "hotel"
    allowed_domains = ["avignon-tourisme.com"]
    output_file = "hotel3.csv"
    if os.path.exists(output_file):
        os.remove(output_file)
    # ✅ URLs des 13 pages (1 principale + 12 paginées)
    start_urls = [
        "https://avignon-tourisme.com/preparez-votre-sejour/hebergements/"
    ] + [
        f"https://avignon-tourisme.com/preparez-votre-sejour/hebergements/?listpage={i}" for i in range(2, 13)
    ]

    def parse(self, response):
        """Scraper les hôtels sur chaque page"""
        hotels = response.css("div.item-wrapper")  # Liste des hôtels sur la page
        page_number = response.url.split("=")[-1] if "=" in response.url else "1"  # ✅ Numéro de page

        hotels_found = 0  # ✅ Compteur pour vérifier combien d'hôtels sont extraits

        for hotel in hotels:
            name = hotel.css("div.item-infos-title::text").get()
            if name:
                name = name.strip()

            hotel_url = hotel.css("a::attr(href)").get()
            if hotel_url and not hotel_url.startswith("http"):
                hotel_url = response.urljoin(hotel_url)

            if hotel_url:
                hotels_found += 1
                yield response.follow(hotel_url, callback=self.parse_hotel, meta={
                    "name": name,
                    "hotel_url": hotel_url,
                    "page": page_number  # ✅ Ajout du numéro de page
                })

        self.logger.info(f"✅ Page {page_number} - Hôtels récupérés : {hotels_found}")

    def parse_hotel(self, response):
        """Scraper les détails de chaque hôtel"""
        name = response.meta.get("name")
        hotel_url = response.meta.get("hotel_url")
        page = response.meta.get("page")  # ✅ Numéro de page

        # ✅ Adresse
        address = response.css("span.localisation-address::text").get()
        address = address.strip() if address else "Non disponible"

         # ✅ Correction de l'extraction du type de logement
        type_logement = response.css("p.item-infos-type::text").get()
        
        # ✅ Si aucun type trouvé avec CSS, on tente avec XPath
        if not type_logement:
            type_logement = response.xpath("//p[contains(@class, 'item-infos-type')]/text()").get()
        
        # ✅ Nettoyage des espaces et retours à la ligne
        type_logement = type_logement.strip() if type_logement else "Non disponible"

        # ✅ **Correction de l'extraction des prix**
        prices = []

        # 1️⃣ **Prix "À partir de X€"**
        starting_price = response.css("span.price-value.text-primary::text").getall()
        if starting_price:
            prices.append(f"À partir de {starting_price[0]}€")

        # 2️⃣ **Fourchette de prix "De X€ à Y€"**
        price_ranges = response.css("span.price-description.text-darkgray::text").getall()
        if price_ranges:
            prices.extend([p.replace("€", "").strip() for p in price_ranges])

        # 3️⃣ **Prix avec labels spéciaux (Week-end, Taxe, etc.)**
        special_prices = response.css("div.price-row div.flex-container.flex-dir-column")
        for item in special_prices:
            label = item.css("span::text").get()
            value = item.css("span.price-value.text-primary::text").getall()
            if label and value:
                price_text = f"{label.strip()} : {' à '.join(value)}€"
                prices.append(price_text)

        # 4️⃣ **Suppléments éventuels**
        supplement = response.css("div.complement-price::text").get()
        if supplement:
            prices.append(supplement.strip())

        # ✅ Format final des prix
        final_price = " | ".join(prices) if prices else "Non disponible"

        # ✅ Équipements
        equipments = response.css("div.equipment-item span::text").getall()
        equipments = " | ".join([eq.strip() for eq in equipments]) if equipments else "Non disponible"

        # ✅ Capacité formatée
        room_count = response.css("div.cell.capacity-item span::text").get()
        capacity_count = response.css("div.cell.capacity-item span::text").getall()

        rooms = room_count.strip() if room_count else "Non disponible"
        capacity = capacity_count[1].strip() if len(capacity_count) > 1 else "Non disponible"
        formatted_capacity = f"{rooms} chambre(s) pour {capacity} personnes"

        # ✅ Périodes d’ouverture
        opening_periods = response.css("div.woody-component-sheet-opening div.cell::text").get()
        opening_periods = opening_periods.strip() if opening_periods else "Non disponible"

        yield {
            "name": name,
            "type": type_logement,
            "price": final_price,
            "address": address,
            "equipments": equipments,
            "formatted_capacity": formatted_capacity,
            "opening_periods": opening_periods
        }
