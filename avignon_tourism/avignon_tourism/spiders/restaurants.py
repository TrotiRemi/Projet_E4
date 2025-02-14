import scrapy
import re

class RestaurantsSpider(scrapy.Spider):
    name = "restaurants"
    start_urls = ["https://avignon-tourisme.com/a-faire-sur-place/restaurants/"] + \
                 [f"https://avignon-tourisme.com/a-faire-sur-place/restaurants/?listpage={i}" for i in range(2, 9)]

    def parse(self, response):
        for restaurant in response.css(".item_sheet_alpha"):
            link = restaurant.css("a::attr(href)").get()
            if link:
                yield response.follow(link, self.parse_restaurant)
    
    def parse_restaurant(self, response):
        def clean_text(text):
            """Nettoie le texte en supprimant les retours à la ligne et espaces superflus."""
            return " ".join(text.split()).strip() if text else "N/A"

        description = response.css(".sheet-global-motto strong::text").get()
        if not description:
            description = response.css("#hide-after-open-details::text").get()

        price_min = response.css(".price-value.text-primary::text").get()
        price_min = clean_text(price_min) if price_min else "N/A"
        
        rating = response.css(".fairguest-condensed-mark .mark::text").get()
        rating_text = response.css(".fairguest-condensed-mark .rating-text::text").get()
        full_rating = f"{clean_text(rating)} {clean_text(rating_text)}" if rating else "N/A"

        phone = response.css(".reveal-phone::attr(href)").get()
        address = response.css(".localisation-address::text").get()
        opening_hours = response.css(".sheet-part-opening .grid-x .cell span::text").getall()

        yield {
            "name": clean_text(response.css("meta[property='og:title']::attr(content)").get()),
            "description": clean_text(description),
            "price_min": price_min,
            "rating": full_rating,
            "phone": clean_text(phone.replace("tel:", "")) if phone else "N/A",
            "address": clean_text(address),
            "opening_hours": clean_text(" | ".join(opening_hours)) if opening_hours else "N/A",
        }