import scrapy

class RestaurantsSpider(scrapy.Spider):
    name = "restau2"
    allowed_domains = ["grandavignon-destinations.fr"]
    start_urls = [
        "https://www.grandavignon-destinations.fr/gastronomie/restaurants/",
        "https://www.grandavignon-destinations.fr/gastronomie/restaurants/page/2/",
        "https://www.grandavignon-destinations.fr/gastronomie/restaurants/page/3/",
        "https://www.grandavignon-destinations.fr/gastronomie/restaurants/page/4/",
        "https://www.grandavignon-destinations.fr/gastronomie/restaurants/page/5/",
    ]

    def parse(self, response):
        for restaurant in response.css("div.wpet-block-list__offer"):
            name = restaurant.css("div.iris-card::attr(data-layer-wpet-offer-title)").get()
            image = restaurant.css("div.iris-card__media img::attr(src)").get()
            rating = restaurant.css("span.iris-card__label::text").get()
            url = restaurant.css("div.iris-card__wrapper::attr(data-a11y-link)").get()
            
            if url:
                yield response.follow(url, callback=self.parse_details, meta={
                    'name': name,
                    'image': image,
                    'rating': rating,
                    'url': url
                })

    def parse_details(self, response):
        # Extraction des horaires d'ouverture
        opening_hours = []
        for row in response.css("table tbody tr"):
            day = row.css("th::text").get()
            hours = row.css("td::text").get()
            if day and hours:
                opening_hours.append(f"{day}: {hours}")

        yield {
            "name": response.meta['name'],
            "image": response.meta['image'],
            "rating": response.meta['rating'],
            "phone": response.css("a.GtmButtonContactTelephonePrestataire::attr(href)").get(),
            "address": response.css("div.wpet-address__datas__content::text").get(),
            "languages": response.xpath("//div[contains(text(), 'Nous parlons')]//text()").get(),
            "specialties": response.css("#le-restaurant ul li::text").getall(),
            "capacity": response.css("#capacite .wp-block-wp-etourisme-v3-icon-label-value::text").getall(),
            "opening_hours": opening_hours,
            "pricing": response.css("#tarifs table tbody tr td::text").getall(),
            "payment_methods": response.css("#tarifs .wpet-list-tags__list li::text").getall(),
            "equipement_et_service": response.css("#prestations .wpet-list-tags__list li::text").getall()
        }

# Pour exécuter ce script, enregistrez-le sous le nom `restaurants_spider.py`
# Ensuite, exécutez la commande suivante dans un terminal :
# scrapy runspider restaurants_spider.py -o restaurants.json