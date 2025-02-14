import scrapy

class AvignonBarsSpider(scrapy.Spider):
    name = "bars"
    allowed_domains = ["avignon-tourisme.com"]
    start_urls = ["https://avignon-tourisme.com/a-faire-sur-place/boire-un-verre/"]

    def parse(self, response):
        bars = response.css("div.item-wrapper")  # Sélection des bars

        for bar in bars:
            name = bar.css("article a img::attr(title)").get()
            if name:
                name = name.strip()

            bar_url = bar.css("a::attr(href)").get()
            if bar_url and not bar_url.startswith("http"):
                bar_url = response.urljoin(bar_url)

            if bar_url:
                yield response.follow(bar_url, callback=self.parse_bar, meta={"name": name, "bar_url": bar_url})

        # **Gestion de la pagination**
        current_page = response.url.split("listpage=")[-1] if "listpage=" in response.url else "1"
        try:
            current_page = int(current_page)
            if current_page < 12:
                next_page = f"https://avignon-tourisme.com/a-faire-sur-place/boire-un-verre/?listpage={current_page + 1}"
                yield response.follow(next_page, callback=self.parse)
        except ValueError:
            pass  

    def parse_bar(self, response):
        """Scraper les informations détaillées de chaque bar."""
        name = response.meta.get("name")
        bar_url = response.meta.get("bar_url")

        # Note client
        rating = response.css("div.item-infos-fairguest span.rating::text").get()
        if rating:
            rating = rating.strip()

        # Adresse
        address = response.css("span.localisation-address::text").get()
        if address:
            address = address.strip()

        # Description du bar
        description = response.css("div.sheet-global-motto strong::text").get()
        if description:
            description = description.strip()

        # Services & équipements
        equipments = response.css("div.equipment-item span::text").getall()
        equipments = [equip.strip() for equip in equipments if equip.strip()]

        # Modes de paiement acceptés
        payment_methods = response.css("div.payment-method-item span::text").getall()
        payment_methods = [p.strip() for p in payment_methods if p.strip()]

        # Horaires d'ouverture
        opening_hours = response.css("div.woody-component-sheet-opening div.cell::text").get()
        if opening_hours:
            opening_hours = opening_hours.strip()

        yield {
            "name": name,
            "url": bar_url,
            "rating": rating,
            "address": address,
            "description": description,
            "equipments": equipments,
            "payment_methods": payment_methods,
            "opening_hours": opening_hours
        }
