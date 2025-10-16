#!/usr/bin/env python3
"""
Bulk login validator
- Excel dosyasından username/password/service.url okur
- Opsiyonel per-row XPATH sütunları: email_xpath, password_xpath, login_xpath
- Headless modu destekler (--headless)
- Dinamik beklemeler (WebDriverWait) ile daha stabil etkileşim
- Pop-up / cookie handler entegre
- Çıktı: login_results.xlsx, log: login_logs.txt
"""

import argparse
import sys
import math
import time
import logging
import pandas as pd
from pathlib import Path
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoAlertPresentException, StaleElementReferenceException, TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------
# Argparse
# --------------------
parser = argparse.ArgumentParser(description="Bulk login validator")
parser.add_argument("excel", nargs="?", help="Excel dosya yolu (örnek: accounts.xlsx)")
parser.add_argument("--headless", action="store_true", help="Chrome'u headless modda çalıştır")
parser.add_argument("--wait", type=int, default=12, help="WebDriverWait timeout (saniye). Varsayılan: 12")
args = parser.parse_args()

def find_latest_xlsx_in_cwd():
    cwd = Path.cwd()
    files = [p for p in cwd.glob("*.xlsx") if not p.name.startswith("~") and not p.name.startswith(".")]
    if not files:
        return None
    files_sorted = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    return str(files_sorted[0])

if args.excel:
    EXCEL_PATH = args.excel
else:
    auto_found = find_latest_xlsx_in_cwd()
    if auto_found:
        EXCEL_PATH = auto_found
    else:
        print("Çalışma dizininde hiçbir .xlsx dosyası bulunamadı. Lütfen Excel dosyasını argüman olarak verin.")
        sys.exit(1)

WAIT_TIME = args.wait
HEADLESS = args.headless

print(f"Kullanılacak Excel dosyası: {EXCEL_PATH}")
print(f"Headless: {HEADLESS} | Wait timeout: {WAIT_TIME}s")

# --------------------
# Logging
# --------------------
logging.basicConfig(
    filename='login_logs.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S'
)

# --------------------
# Popup / cookie handler
# --------------------
def handle_popups(driver):
    """Sayfada çıkan çerez izinleri, modal ve alert'leri kapatmaya çalışır."""
    action = ActionChains(driver)
    # 1) JS alert varsa kapat
    try:
        alert = driver.switch_to.alert
        try:
            alert.dismiss()
        except Exception:
            try:
                alert.accept()
            except Exception:
                pass
    except NoAlertPresentException:
        pass
    except Exception:
        pass

    # 2) Yaygın buton metinleri (Türkçe + İngilizce)
    selectors = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'kabul')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tamam')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close')]",
        "//*[contains(@class,'cookie') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//*[contains(@id,'cookie') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//*[contains(@class,'consent')]", 
        "//*[contains(@id,'consent')]",
        "//*[@role='dialog']//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//*[@aria-label='close']",
        "//button[contains(@class,'close') or contains(@class,'btn-close')]"
    ]

    for sel in selectors:
        try:
            elements = driver.find_elements(By.XPATH, sel)
            for el in elements:
                try:
                    if el.is_displayed():
                        try:
                            el.click()
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", el)
                            except Exception:
                                pass
                        time.sleep(0.25)
                except StaleElementReferenceException:
                    continue
        except Exception:
            continue

    # 3) iframe içindeki butonlara bakmak (basit deneme)
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in iframes:
            try:
                driver.switch_to.frame(frame)
                for txt in ["accept","kabul","agree","tamam","close","kapat","ok","got it"]:
                    try:
                        btns = driver.find_elements(By.XPATH, f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{txt}')] | //a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{txt}')]")
                        for b in btns:
                            try:
                                if b.is_displayed():
                                    try:
                                        b.click()
                                    except Exception:
                                        driver.execute_script("arguments[0].click();", b)
                                    time.sleep(0.25)
                            except Exception:
                                continue
                    except Exception:
                        continue
                driver.switch_to.default_content()
            except Exception:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
    except Exception:
        pass

    # 4) ESC tuşu gönder
    try:
        action.send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass

    # 5) Overlay'leri DOM'dan kaldırma (genel ve riskli; gerektiğinde devre dışı bırakabilirsin)
    overlay_scripts = [
        "document.querySelectorAll('[role=\"dialog\"]').forEach(e=>e.remove());",
        "document.querySelectorAll('.modal').forEach(e=>e.remove());",
        "document.querySelectorAll('.cookie-banner').forEach(e=>e.remove());",
        "document.querySelectorAll('[id*=\"cookie\"]').forEach(e=>e.remove());",
        "document.querySelectorAll('[class*=\"cookie\"]').forEach(e=>e.remove());"
    ]
    for script in overlay_scripts:
        try:
            driver.execute_script(script)
        except Exception:
            pass

    time.sleep(0.4)

# --------------------
# Excel okuma (header'lı veya fallback F/G davranışı)
# --------------------
df = None
username_col = None
password_col = None
service_col = None

try:
    df_try = pd.read_excel(EXCEL_PATH, engine="openpyxl", header=0)
    cols_lower = {str(c).strip().lower(): c for c in df_try.columns}
    def pick_col(mapping, *candidates):
        for cand in candidates:
            key = cand.strip().lower()
            if key in mapping:
                return mapping[key]
        return None
    username_col = pick_col(cols_lower, "username", "login", "user", "email", "kullanici", "kullanıcı")
    password_col = pick_col(cols_lower, "password", "pass", "pwd", "sifre", "şifre")
    service_col  = pick_col(cols_lower, "service.url", "service_url", "url", "site", "website", "domain", "service", "login_url")
    # also detect optional per-row xpath columns if present
    email_xpath_col = pick_col(cols_lower, "email_xpath", "email-xpath", "emailxpath")
    password_xpath_col = pick_col(cols_lower, "password_xpath", "password-xpath", "passwordxpath")
    login_xpath_col = pick_col(cols_lower, "login_xpath", "login-xpath", "loginxpath")

    if username_col and password_col and service_col:
        df = df_try.copy()
    else:
        df = None
except Exception:
    df = None
    email_xpath_col = None
    password_xpath_col = None
    login_xpath_col = None

if df is None:
    # fallback to original behavior (F/G columns)
    try:
        df = pd.read_excel(EXCEL_PATH, usecols="F,G", header=None, names=["username", "password"], skiprows=1, engine="openpyxl")
        try:
            df_full = pd.read_excel(EXCEL_PATH, engine="openpyxl", header=0)
            cols_lower_full = {str(c).strip().lower(): c for c in df_full.columns}
            service_col = None
            # detect service column in full sheet
            for cand in ["service.url", "service_url", "url", "site", "website", "domain", "service", "login_url"]:
                key = cand.strip().lower()
                if key in cols_lower_full:
                    service_col = cols_lower_full[key]
                    break
            if service_col is None:
                if df_full.shape[1] >= 10:
                    service_col = df_full.columns[9]
                elif df_full.shape[1] >= 8:
                    service_col = df_full.columns[7]
                else:
                    service_col = None
            # detect optional xpath columns in full sheet
            if service_col:
                email_xpath_col = None
                password_xpath_col = None
                login_xpath_col = None
                for cand in ["email_xpath", "email-xpath", "emailxpath"]:
                    if cand in cols_lower_full:
                        email_xpath_col = cols_lower_full[cand]
                        break
                for cand in ["password_xpath", "password-xpath", "passwordxpath"]:
                    if cand in cols_lower_full:
                        password_xpath_col = cols_lower_full[cand]
                        break
                for cand in ["login_xpath", "login-xpath", "loginxpath"]:
                    if cand in cols_lower_full:
                        login_xpath_col = cols_lower_full[cand]
                        break
        except Exception:
            service_col = None
    except Exception as e:
        print(f"Excel okuma hatası: {e}")
        sys.exit(1)

if df is None:
    print("Excel dosyasında gerekli sütunlar bulunamadı.")
    sys.exit(1)

if username_col is None:
    if "username" in df.columns:
        username_col = "username"
if password_col is None:
    if "password" in df.columns:
        password_col = "password"

if service_col is None:
    print("Excel'de service.url sütunu bulunamadı. Lütfen 'service.url' veya benzeri bir başlık ekleyin.")
    sys.exit(1)

# If service_col not inside df (fallback case), try to merge from full sheet
if service_col not in df.columns:
    try:
        df_full = pd.read_excel(EXCEL_PATH, engine="openpyxl", header=0)
        if service_col in df_full.columns:
            df_full = df_full.reset_index(drop=True)
            df = df.reset_index(drop=True)
            if len(df) == len(df_full):
                df[service_col] = df_full[service_col]
            else:
                df[service_col] = df_full[service_col].reindex(df.index).fillna("")
        else:
            print("Service sütunu bulundu fakat değeri alınamadı.")
            sys.exit(1)
    except Exception as e:
        print(f"Service sütunu okunurken hata: {e}")
        sys.exit(1)

# ensure optional xpath column names exist (if detected earlier but not in df, try to attach)
# Try to attach xpath columns from full sheet if missing
optional_xpath_cols = {}
try:
    df_full  # may not exist
    for col_var, cand_names in (("email_xpath_col", ["email_xpath","email-xpath","emailxpath"]),
                                ("password_xpath_col", ["password_xpath","password-xpath","passwordxpath"]),
                                ("login_xpath_col", ["login_xpath","login-xpath","loginxpath"])):
        val = locals().get(col_var)
        if val is None:
            for cand in cand_names:
                if cand in df_full.columns:
                    optional_xpath_cols[col_var] = df_full.columns[list(df_full.columns).index(cand)]
                    break
        else:
            optional_xpath_cols[col_var] = val
except Exception:
    # ignore; optional cols may not be present
    optional_xpath_cols = {}

# normalize assigned optional columns
email_xpath_col = optional_xpath_cols.get("email_xpath_col", email_xpath_col)
password_xpath_col = optional_xpath_cols.get("password_xpath_col", password_xpath_col)
login_xpath_col = optional_xpath_cols.get("login_xpath_col", login_xpath_col)

if 'status' not in df.columns:
    df['status'] = ""

print(f"Toplam {len(df)} hesap test edilecek")

# --------------------
# Tarayıcı ayarları
# --------------------
chrome_options = webdriver.ChromeOptions()
if HEADLESS:
    chrome_options.add_argument("--headless=new")  # modern headless if available
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, WAIT_TIME)

# --------------------
# Varsayılan XPATH'ler ve fallback selector listeleri
# --------------------
# (Orijinal davranışı korumak için varsayılanları bıraktım, ama daha genel fallback'lar ekledim)
DEFAULT_XPATHS = {
    'email': "//input[@id='eMkroEmail']",
    'password': "//input[@id='eMkroPassword']",
    'login_button': "//span[contains(.,'Giriş Yap')]"
}

FALLBACK_EMAIL_SELECTORS = [
    "//input[@type='email']",
    "//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'email')]",
    "//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'email')]",
    "//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'user')]",
    "//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'user')]",
    "//input[@type='text']"
]

FALLBACK_PASSWORD_SELECTORS = [
    "//input[@type='password']",
    "//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'pass')]",
    "//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'pass')]"
]

FALLBACK_LOGIN_BUTTON_SELECTORS = [
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'giriş')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'giris')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
    "//input[@type='submit']",
    "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'giriş')]"
]

def choose_xpath_for_field(row, col_name, default_key, fallback_list):
    """
    row: pandas Series
    col_name: name of optional xpath column (may be None)
    default_key: key in DEFAULT_XPATHS
    fallback_list: list of fallback xpaths to try if default fails
    """
    # 1) if per-row xpath column exists and has a value, use it
    if col_name and (col_name in row.index):
        val = row[col_name]
        if isinstance(val, str) and val.strip():
            return val.strip()

    # 2) use DEFAULT_XPATHS
    default = DEFAULT_XPATHS.get(default_key)
    if default:
        return default

    # 3) if no default available, return first fallback
    return fallback_list[0] if fallback_list else None

def find_element_with_fallback(driver, wait, xpath_candidates, timeout=WAIT_TIME):
    """
    Try candidates in order: for each, wait for presence and return element.
    If none found, raise NoSuchElementException.
    """
    last_exc = None
    for xp in xpath_candidates:
        try:
            el = wait.until(EC.presence_of_element_located((By.XPATH, xp)))
            return el
        except TimeoutException as te:
            last_exc = te
            continue
        except Exception as e:
            last_exc = e
            continue
    raise NoSuchElementException(f"None of the xpaths matched. Last error: {last_exc}")

# --------------------
# Ana döngü
# --------------------
for index, row in df.iterrows():
    # read credentials and site
    username = ""
    password = ""
    site_raw = ""
    try:
        username = str(row[username_col]).strip() if username_col in row.index else str(row.get("username","")).strip()
    except Exception:
        username = str(row.get("username","")).strip()
    try:
        password = str(row[password_col]).strip() if password_col in row.index else str(row.get("password","")).strip()
    except Exception:
        password = str(row.get("password","")).strip()
    try:
        site_raw = row[service_col] if service_col in row.index else row.get(service_col, "")
    except Exception:
        site_raw = row.get(service_col, "")

    def normalize_url(u):
        if u is None:
            return ""
        if isinstance(u, float) and math.isnan(u):
            return ""
        s = str(u).strip()
        if not s:
            return ""
        if not s.startswith(("http://", "https://")):
            s = "https://" + s
        return s

    site = normalize_url(site_raw)

    print(f"\n{index+1}/{len(df)} - Denenen hesap: {username} | Site: {site}")
    logging.info(f"Denenen hesap: {username} | Site: {site}")

    try:
        if not site:
            status = "500 - Boş/Geçersiz Site URL"
            print(status)
            logging.error(status)
            df.at[index, 'status'] = status
            continue

        driver.get(site)

        # kısa bekleme ve popup handling
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except Exception:
            pass
        handle_popups(driver)

        # Determine XPATHs to use for this row
        email_xpath = choose_xpath_for_field(row, email_xpath_col, "email", FALLBACK_EMAIL_SELECTORS)
        password_xpath = choose_xpath_for_field(row, password_xpath_col, "password", FALLBACK_PASSWORD_SELECTORS)
        login_xpath = choose_xpath_for_field(row, login_xpath_col, "login_button", FALLBACK_LOGIN_BUTTON_SELECTORS)

        # Prepare candidate lists (prioritize chosen selector, then defaults/fallbacks)
        email_candidates = []
        if isinstance(email_xpath, str) and email_xpath.strip():
            email_candidates.append(email_xpath)
        email_candidates.extend([s for s in FALLBACK_EMAIL_SELECTORS if s not in email_candidates])

        password_candidates = []
        if isinstance(password_xpath, str) and password_xpath.strip():
            password_candidates.append(password_xpath)
        password_candidates.extend([s for s in FALLBACK_PASSWORD_SELECTORS if s not in password_candidates])

        login_candidates = []
        if isinstance(login_xpath, str) and login_xpath.strip():
            login_candidates.append(login_xpath)
        login_candidates.extend([s for s in FALLBACK_LOGIN_BUTTON_SELECTORS if s not in login_candidates])

        # find email input
        try:
            email_el = find_element_with_fallback(driver, wait, email_candidates)
            try:
                email_el.clear()
            except Exception:
                pass
            email_el.send_keys(username)
        except Exception as e:
            # log and mark error, but attempt to continue to password if possible
            logging.error(f"{index+1} - Email input bulunamadı: {e}")
            status = "500 - Email input bulunamadı"
            print(status)
            df.at[index, 'status'] = status
            continue

        # find password input
        try:
            password_el = find_element_with_fallback(driver, wait, password_candidates)
            try:
                password_el.clear()
            except Exception:
                pass
            password_el.send_keys(password)
        except Exception as e:
            logging.error(f"{index+1} - Password input bulunamadı: {e}")
            status = "500 - Password input bulunamadı"
            print(status)
            df.at[index, 'status'] = status
            continue

        # find and click login button (try clickable)
        clicked = False
        last_login_exc = None
        for xp in login_candidates:
            try:
                # wait until clickable if possible
                try:
                    btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                except Exception:
                    # fallback to presence
                    btn = wait.until(EC.presence_of_element_located((By.XPATH, xp)))
                try:
                    btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", btn)
                clicked = True
                break
            except Exception as exc:
                last_login_exc = exc
                continue

        if not clicked:
            logging.error(f"{index+1} - Login butonuna tıklanamadı. Hatalar: {last_login_exc}")
            status = "500 - Login butonu bulunamadı/kliklenemedi"
            print(status)
            df.at[index, 'status'] = status
            continue

        # bekle ve sonuç kontrolü
        try:
            # kısa süre bekle sayfa değişsin
            time.sleep(2)
            # check for success keywords in url or page source
            page_src = driver.page_source.lower()
            current_url = driver.current_url.lower()
            if any(keyword in current_url or keyword in page_src for keyword in ["anasayfa", "dashboard", "welcome", "hoşgeldiniz", "hosgeldiniz"]):
                status = "200 - Başarılı Giriş"
                print(status)
                logging.info(status)
            else:
                # hata mesajı ara (yerel dilde gelen anahtar kelimeler)
                try:
                    error_elements = driver.find_elements(By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'hatalı') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'yanlış') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'invalid') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'incorrect')]")
                except Exception:
                    error_elements = []
                if error_elements:
                    status = "404 - Kullanıcı/Şifre Hatalı"
                    try:
                        error_msg = error_elements[0].text.strip()[:80] + "..." if error_elements[0].text else ""
                    except Exception:
                        error_msg = ""
                    print(f"{status} | Mesaj: {error_msg}")
                    logging.warning(f"{status} | Mesaj: {error_msg}")
                else:
                    status = "404 - Bilinmeyen Hata"
                    print(status)
                    logging.warning(status)
        except Exception as e:
            status = f"500 - Sonuç kontrol hatası: {str(e)[:80]}"
            print(status)
            logging.error(status)

        df.at[index, 'status'] = status

    except Exception as e:
        error_msg = f"500 - Sistem Hatası: {str(e)[:120]}"
        print(error_msg)
        logging.error(error_msg)
        df.at[index, 'status'] = error_msg

# --------------------
# Temizlik ve sonuç kaydetme
# --------------------
try:
    driver.quit()
except Exception:
    pass

out_file = "login_results.xlsx"
df.to_excel(out_file, index=False)
print(f"\nTest tamamlandı! Sonuçlar: {out_file}")
