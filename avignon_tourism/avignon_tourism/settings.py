from shutil import which
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

BOT_NAME = "avignon_tourism"

SPIDER_MODULES = ["avignon_tourism.spiders"]
NEWSPIDER_MODULE = "avignon_tourism.spiders"

# Configuration de Selenium
LOG_LEVEL = 'DEBUG'
SELENIUM_DRIVER_NAME = 'chrome'
SELENIUM_DRIVER_SERVICE = Service(ChromeDriverManager().install())  # Utilisation correcte du Service()
SELENIUM_DRIVER_ARGUMENTS = ['--headless', '--no-sandbox', '--disable-dev-shm-usage']  # Options pour exécuter Chrome sans interface graphique
# Activation du middleware Selenium pour Scrapy
DOWNLOADER_MIDDLEWARES = {
    'scrapy_selenium.SeleniumMiddleware': 800,
}
ITEM_PIPELINES = {
    'avignon_tourism.pipelines_act.FormatDataPipeline': 300,
}
ITEM_PIPELINES = {
    'avignon_tourism.pipelines_hotel.HotelPipeline': 300,
}
ITEM_PIPELINES = {
    'avignon_tourism.pipelines_restau.CleanRestaurantPipeline': 300,
}

# Respecte le fichier robots.txt du site web
ROBOTSTXT_OBEY = True

# Configuration avancée
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
