import scrapy

class AvignonHotelsSpider(scrapy.Spider):
    name = "hotels"
    allowed_domains = ["avignon-tourisme.com"]
    start_urls = ["https://avignon-tourisme.com/preparez-votre-sejour/hebergements/"]

    def parse(self, response):
        hotels = response.css("div.item-wrapper")  # Sélection des hôtels

        for hotel in hotels:
            name = hotel.css("div.item-infos-title::text").get()
            if name:
                name = name.strip()

            hotel_url = hotel.css("a::attr(href)").get()
            if hotel_url and not hotel_url.startswith("http"):
                hotel_url = response.urljoin(hotel_url)

            if hotel_url:
                yield response.follow(hotel_url, callback=self.parse_hotel, meta={"name": name, "hotel_url": hotel_url})

        # **Gestion de la pagination (Pages 2 à 12)**
        current_page = response.url.split("listpage=")[-1] if "listpage=" in response.url else "1"
        try:
            current_page = int(current_page)
            if current_page < 12:
                next_page = f"https://avignon-tourisme.com/preparez-votre-sejour/hebergements/?listpage={current_page + 1}"
                yield response.follow(next_page, callback=self.parse)
        except ValueError:
            pass  

    def parse_hotel(self, response):
        """Scraper les informations détaillées de chaque hôtel."""
        name = response.meta.get("name")
        hotel_url = response.meta.get("hotel_url")

        # Nombre d'étoiles
        stars = len(response.css("div.item-infos-ratings span.icon-font-e909"))

        # Note client
        rating = response.css("div.item-infos-fairguest span.rating::text").get()
        if rating:
            rating = rating.strip()

        # Adresse
        address = response.css("span.localisation-address::text").get()
        if address:
            address = address.strip()

        # Prix (chambre double)
        price = response.css("span.fat-price::text").get()
        if price:
            price = price.strip()

        # Description de l'hôtel
        description = response.css("div.sheet-global-motto strong::text").get()
        if description:
            description = description.strip()

        # Services & équipements
        equipments = response.css("div.equipment-item span::text").getall()
        equipments = [equip.strip() for equip in equipments if equip.strip()]

        # Nombre de chambres
        capacity = response.css("div.capacity-item span::text").get()
        if capacity:
            capacity = capacity.strip()

        # Modes de paiement acceptés
        payment_methods = response.css("div.payment-method-item span::text").getall()
        payment_methods = [p.strip() for p in payment_methods if p.strip()]

        # Périodes d'ouverture
        opening_periods = response.css("div.woody-component-sheet-opening div.cell::text").get()
        if opening_periods:
            opening_periods = opening_periods.strip()

        yield {
            "name": name,
            "url": hotel_url,
            "stars": stars,
            "rating": rating,
            "price": price,
            "address": address,
            "description": description,
            "equipments": equipments,
            "capacity": capacity,
            "payment_methods": payment_methods,
            "opening_periods": opening_periods
        }
