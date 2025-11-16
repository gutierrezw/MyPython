from selenium import webdriver
from bs4 import BeautifulSoup

driver = webdriver.Chrome()
driver.get("https://www.gurufocus.com/stock/HASI/summary")

html = driver.page_source
soup = BeautifulSoup(html, "html.parser")
tabla = soup.find("table")
print(tabla.text)


# ... buscar texto Dividend Growth Rate (5Y)
driver.quit()

