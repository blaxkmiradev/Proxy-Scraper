import requests
import re
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor
from colorama import init, Fore, Style


init(autoreset=True)


CONFIG_FILE = "config.json"
TIMEOUT = 5
MAX_THREADS = 50
HEADERS = {"User-Agent": "Mozilla/5.0"}
proxy_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b")



def load_or_create_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        print(Fore.CYAN + "=== Setup Configuration ===")
        config = {
            "TELEGRAM_TOKEN": input(Fore.YELLOW + "Enter Telegram Bot Token: ").strip(),
            "TELEGRAM_CHAT_ID": input(Fore.YELLOW + "Enter Telegram Chat ID: ").strip(),
            "DISCORD_WEBHOOK": input(Fore.YELLOW + "Enter Discord Webhook URL (or leave blank): ").strip()
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        return config


def load_urls():
    if not os.path.exists("url.txt"):
        print(Fore.RED + "[ERROR] url.txt not found!")
        return []
    with open("url.txt") as f:
        return [x.strip() for x in f if x.strip()]


def fetch(url):
    try:
        return requests.get(url, headers=HEADERS, timeout=10).text
    except:
        return ""


def scrape(url):
    print(Fore.BLUE + f"[SCRAPE] {url}")
    data = fetch(url)
    return set(proxy_pattern.findall(data))


def check_proxy(proxy):
    protocols = {
        "HTTP": f"http://{proxy}",
        "HTTPS": f"http://{proxy}",
        "SOCKS4": f"socks4://{proxy}",
        "SOCKS5": f"socks5://{proxy}",
    }

    for proto, p in protocols.items():
        try:
            start = time.time()
            r = requests.get(
                "http://httpbin.org/ip",
                proxies={"http": p, "https": p},
                timeout=TIMEOUT,
            )
            latency = round((time.time() - start) * 1000, 2)
            if r.status_code == 200:
                return {
                    "proxy": proxy,
                    "type": proto,
                    "latency": latency
                }
        except:
            continue
    return None


def send_telegram(msg, token, chat_id):
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg})
    except:
        pass


def send_discord(msg, webhook):
    if not webhook:
        return
    try:
        requests.post(webhook, json={"content": msg})
    except:
        pass



def main():
    print(Fore.MAGENTA + Style.BRIGHT + "=== Rikixz Proxy Scraper ===")
    config = load_or_create_config()
    urls = load_urls()
    if not urls:
        return

    proxies = set()

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(scrape, urls)
    for r in results:
        proxies.update(r)
    print(Fore.GREEN + f"[+] Scraped {len(proxies)} proxies")

    live = []


    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        results = executor.map(check_proxy, proxies)

    for result in results:
        if result:
            proxy = result["proxy"]
            ptype = result["type"]
            latency = result["latency"]

            msg = f"[LIVE] {proxy} | {ptype} | {latency}ms"
            print(Fore.CYAN + msg)
            live.append(msg)

            send_telegram(msg, config["TELEGRAM_TOKEN"], config["TELEGRAM_CHAT_ID"])
            send_discord(msg, config["DISCORD_WEBHOOK"])


    with open("checked.txt", "w") as f:
        for line in live:
            f.write(line + "\n")

    print(Fore.GREEN + f"[+] Saved {len(live)} live proxies to checked.txt")


if __name__ == "__main__":
    main()
