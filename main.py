import requests
from bs4 import BeautifulSoup
import json
import gspread
from google.oauth2 import service_account
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
from config import GSHEET_CREDENTIALS_PATH, URL_FOR_GSHEET, SHEET


URL_FOR_PARSING = 'https://store.steampowered.com/sale/quebec2023'
BUTTON_CSS_SELECTOR = '#SaleSection_31537 > div.partnersaledisplay_SaleSection_2NfLq.eventbbcodeparser_SaleSectionCtn_2Xrw_.SaleSectionForCustomCSS > div.saleitembrowser_SaleItemBrowserContainer_2wLns > div:nth-child(2) > div.facetedbrowse_FacetedBrowseInnerCtn_hWbTI > div > div.saleitembrowser_ShowContentsContainer_3IRkb > button'


def get_game_details(steam_id):
    response = requests.get(f'https://store.steampowered.com/api/appdetails/?appids={steam_id}')
    if response.ok:
        steam_data = response.json()
        details = steam_data.get(steam_id, {})
        if details.get('success'):
            link = f'https://store.steampowered.com/app/{steam_id}'
            game_info = details.get('data', {})
            game_name = game_info.get('name')
            game_type = game_info.get('type')
            release_date = game_info.get('release_date',{}).get('date')
            game_website = game_info.get('website')
            developer = '\n'.join(map(str, game_info.get('developers')))
            publisher = '\n'.join(map(str, game_info.get('publishers')))
            platforms_list = []
            platforms_info = game_info.get('platforms', {})
            for os, supported in platforms_info.items():
                if platforms_info[os]:
                    platforms_list.append(os)
            platforms = ', '.join(map(str, platforms_list))
            genres_list = []
            for genre in game_info.get('genres', {}):
                genres_list.append(genre.get('description'))
            genres = ', '.join(map(str, genres_list))
            email = game_info.get('support_info', {}).get('email')
            return [link, game_name, game_type, release_date, game_website, developer, publisher, platforms, genres, email, steam_id]

def get_game_ids(page_source):
    soup = BeautifulSoup(page_source, 'lxml')
    rows = soup.find('div', class_='facetedbrowse_FacetedBrowseItems_NO-IP').find_all('div', class_='salepreviewwidgets_SaleItemBrowserRow_y9MSd')
    game_ids = set()
    for row in rows:
        link = row.find('div', class_='ImpressionTrackedElement').find('div', class_='salepreviewwidgets_StoreSaleWidgetOuterContainer_38DqR Panel Focusable').find('div', class_='salepreviewwidgets_StoreSaleWidgetContainer_UlvFk salepreviewwidgets_SaleItemDefaultCapsuleDisplay_34o91 Focusable').find('div', class_='salepreviewwidgets_StoreSaleWidgetHalfLeft_2Va3O').find('a')
        game_ids.add(link.get('href').replace('https://store.steampowered.com/app/','').split('/')[0])
    return game_ids


def get_games_list():
    options = Options()
    options.add_argument("start-maximized")
    options.add_argument("incognito")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(URL_FOR_PARSING)
    WebDriverWait(driver, timeout=10).until(EC.presence_of_all_elements_located
                                            ((By.CSS_SELECTOR, BUTTON_CSS_SELECTOR)))
    while True:
        try:
            WebDriverWait(driver, timeout=20).until(EC.presence_of_all_elements_located
                                                    ((By.CSS_SELECTOR, BUTTON_CSS_SELECTOR)))
            show_more_button = driver.find_element(By.CSS_SELECTOR,
                                                   BUTTON_CSS_SELECTOR)
            if show_more_button:
                WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, BUTTON_CSS_SELECTOR)))
                show_more_button.click()
        except TimeoutException:
            break
    page_source = driver.page_source
    ids = get_game_ids(page_source)
    driver.quit()
    return ids


if __name__ == '__main__':
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    gsheets_creds_path = GSHEET_CREDENTIALS_PATH
    credentials = service_account.Credentials.from_service_account_file(gsheets_creds_path)
    scoped_credentials = credentials.with_scopes(scope)
    gc = gspread.authorize(scoped_credentials)
    sheet = gc.open_by_url(URL_FOR_GSHEET)
    worksheet = sheet.worksheet(SHEET)

    # ADD HEADERS TO SHEET
    #worksheet.append_row(
    # values=['link', 'game_name', 'game_type', 'release_date', 'game_website', 'developer', 'publisher', 'platforms', 'genres', 'email', 'steam_id'])

    already_parsed = worksheet.col_values(11)
    already_parsed.remove('steam_id')

    games = get_games_list()
    print(len(games))
    for game in games:
        if game not in already_parsed:
            worksheet.append_row(values=get_game_details(game))
            time.sleep(2.0)


