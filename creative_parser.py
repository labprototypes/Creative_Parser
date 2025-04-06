import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# === Авторизация Google Sheets ===
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name(
    "creativeparser-455918-93ecc38ccd1c.json", SCOPE
)
client = gspread.authorize(CREDS)
sheet = client.open("CreativeParser").sheet1

# Получаем уже добавленные ссылки, чтобы избежать дублей
existing_links = [row[1] for row in sheet.get_all_values()[1:]]

# === Настройки парсинга ===
BASE_URL = "https://www.adsoftheworld.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TARGET_COUNT = 50
parsed_count = 0
page = 0
new_cases = []

# === Парсим по страницам, пока не соберём нужное количество ===
while parsed_count < TARGET_COUNT:
    page_url = f"{BASE_URL}/latest?page={page}"
    print(f"Парсим страницу: {page_url}")
    response = requests.get(page_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select(".views-row")

    if not cards:
        print("Больше нет кейсов на странице.")
        break

    for card in cards:
        if parsed_count >= TARGET_COUNT:
            break

        title_tag = card.select_one(".title a")
        if not title_tag:
            continue

        title = title_tag.text.strip()
        link = BASE_URL + title_tag['href']

        if link in existing_links:
            print(f"Пропущено (дубликат): {title}")
            continue

        # Парсим страницу кейса
        print(f"Парсим кейс: {title}")
        case_page = requests.get(link, headers=HEADERS)
        case_soup = BeautifulSoup(case_page.text, "html.parser")

        description_tag = case_soup.select_one(".field--name-field-description")
        description = description_tag.text.strip() if description_tag else "Без описания"

        tags_el = case_soup.select(".taxonomy-term")
        tags = ", ".join([el.text.strip() for el in tags_el]) or "Без тегов"

        category_tag = case_soup.select_one(".field--name-field-primary-category")
        category = category_tag.text.strip() if category_tag else "Без категории"

        date_tag = case_soup.select_one("time")
        date = date_tag.text.strip() if date_tag else "N/A"

        new_cases.append([title, link, category, tags, description, date])
        parsed_count += 1
        time.sleep(1.2)  # чтобы не спамить сервер

    page += 1

# === Добавляем новые кейсы в таблицу ===
if new_cases:
    sheet.append_rows(new_cases, value_input_option="USER_ENTERED")
    print(f"✅ Добавлено {len(new_cases)} новых кейсов в Google Sheets")
else:
    print("🔍 Новых кейсов не найдено. Всё уже есть.")
