import sys, os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import json
import requests
from clint.textui import progress
import subprocess

N_m3u8DL_CLI_ver = "2.9.7"


def downloadFile(FileLink, title):
    if FileLink[1] == 0:
        r = requests.get(FileLink[0], headers={'Cache-Control': 'no-cache'}, stream=True)
        if r.status_codes == 200:
            with open(title + '.mp4', 'wb') as f:
                total_length = int(r.headers.get('content-length'))
                for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
                    if chunk:
                        f.write(chunk)
                        f.flush()
    else:
        print(FileLink[0])
        commandDownload = 'N_m3u8DL-CLI_v{N_m3u8DL_CLI_ver}.exe "{url_m3u8}" --workDir "./" --enableDelAfterDone --noProxy --disableDateInfo --saveName "{outputName}"'.format(
            outputName=title, url_m3u8=FileLink[0], N_m3u8DL_CLI_ver=N_m3u8DL_CLI_ver)
        subprocess.call(commandDownload, shell=True)


def extracturl(api):
    api = json.loads(api)
    r = requests.get(api["data"]["mp4"], headers={'Cache-Control': 'no-cache'}, stream=True)
    if str(api).find("subtitles") != -1:
        print("Downloading subtitles...")
        counter = 0
        for subtitles_links in api["data"]["subtitles"]:
            r = requests.get(subtitles_links["url"], allow_redirects=True)
            r.encoding = r.apparent_encoding
            nom_fichier = (api["data"]["title"] + "[" + str(counter) + "].vtt")
            fichier = open(nom_fichier, 'wb')
            fichier.write(r.text.encode('UTF8'))
            fichier.close()
            counter += 1

    if requests.status_codes == 200:
        return [api["data"]["mp4"], 0]
    else:
        return [api["data"]["hls"], 1]


def clean_text(text):
    for ch in ['|', '>', '<', '"', '?', '?', '*', ':', '/', '\\']:
        if ch in text:
            text = text.replace(ch, " ")

    while text.find("  ") != -1:
        text = text.replace("  ", " ")

    return text


def process_browser_logs_for_network_events(logs):
    for entry in logs:
        log = json.loads(entry["message"])["message"]
        if (
                "Network.response" in log["method"]
        ):
            yield log


def initialisation_selenium():
    print("Initiating a chrome session...")
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}

    options = webdriver.ChromeOptions()
    options.add_argument("--mute-audio")
    options.headless = True
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                         'like Gecko) Chrome/85.0.4183.121 Safari/537.36"')
    options.binary_location = r"C:\Program Files\Google\Chrome Beta\Application\chrome.exe"
    driver = webdriver.Chrome(executable_path=r"./chromedriver.exe", options=options, desired_capabilities=caps)
    return driver


def login(username, password, driver):
    print("Connection to BrutX...")
    driver.get("https://home.brutx.com/login")
    driver.find_element_by_xpath('//*[@id="email"]').send_keys(username)
    driver.find_element_by_xpath('//*[@id="password"]').send_keys(password)
    driver.find_element_by_xpath('//*[@id="password"]').send_keys(Keys.ENTER)


def returnAPI_PLAYER(driver, get_url):
    print("Recovering the API_PLAYER file...")
    logs = driver.get_log("performance")
    events = process_browser_logs_for_network_events(logs)

    for event in events:
        try:
            if event["params"]["response"]["url"].startswith("https://home.brutx.com/api/player/"):
                driver.quit()

                headers = {
                    'authority': 'home.brutx.com',
                    'content-length': '0',
                    'accept': '*/*',
                    'x-csrf-token': event["params"]["response"]["requestHeaders"]["x-csrf-token"],
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
                    'x-requested-with': 'XMLHttpRequest',
                    'sec-gpc': '1',
                    'origin': 'https://home.brutx.com',
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-dest': 'empty',
                    'referer': get_url,
                    'accept-language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                    'cookie': event["params"]["response"]["requestHeaders"]["cookie"],
                    'dnt': '1',
                }

                response = requests.post(event["params"]["response"]["url"], headers=headers)

                return response.text
        except Exception:
            pass


def launch():
    os.system('cls')
    driver = initialisation_selenium()
    url = sys.argv[sys.argv.index("-url") + 1]
    username = sys.argv[sys.argv.index("-username") + 1]
    password = sys.argv[sys.argv.index("-password") + 1]
    login(username, password, driver)
    driver.get(url)
    title = driver.find_element_by_xpath('//meta[@property="og:title"]').get_attribute("content")
    titleclean = clean_text(title)
    print("Title of the video: " + title)
    print("Clean title of the video: " + titleclean)
    print("Launch of the video...")
    driver.find_element_by_xpath('/html/body/main/section[1]/div/a/span[1]').click()  # launch video
    time.sleep(3)  # wait for more log
    print("Extraction of the json api...")
    api = returnAPI_PLAYER(driver, url)
    print("Extracting the File link in the json api...")
    fileLink = extracturl(api)
    print("Start downloading the file...")
    downloadFile(fileLink, titleclean)


if __name__ == "__main__":
    launch()
