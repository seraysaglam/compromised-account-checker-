#!/usr/bin/env python3
import argparse
import sys
import math
import time
import logging
import pandas as pd
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoAlertPresentException, StaleElementReferenceException

# --------------------
# Argparse: opsiyonel excel dosyası argümanı
# Eğer verilmezse çalışma dizinindeki en son değiştirilen .xlsx seçilecek
# --------------------
parser = argparse.ArgumentParser(description="Bulk login validator")
parser.add_argument("excel", nargs="?", help="Excel dosya yolu (örnek: accounts.xlsx)")
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

print(f"Kullanılacak Excel dosyası: {EXCEL_PATH}")

# --------------------
# Log ayarları
# --------------------
logging.basicConfig(
    filename='login_logs.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S'
)

# --------------------
# Popup / cookie handler
# --------------------
def handle_popups(driver):
    action = ActionChains(driver)
    # 1) JS alert varsa kapat
    try:
        alert = driver.switch_to.alert
        try:
            alert.dismiss()
        except Exception:
            alert.accept()
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
                        el.click()
                        time.sleep(0.3)
                except StaleElementReferenceException:
                    continue
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(0.3)
                    except Exception:
                        continue
        except Exception:
            continue

    # 3) ESC tuşu gönder (bazı modal'lar kapanır)
    try:
        action.send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass

    # 4) Overlay’leri DOM'dan kaldır
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

    time.sleep(0.5)

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
    if username_col and password_col and service_col:
        df = df_try.copy()
    else:
        df = None
except Exception:
    df = None

if df is None:
    try:
        df = pd.read_excel(EXCEL_PATH, usecols="F,G", header=None, names=["username", "password"], skiprows=1, engine="openpyxl")
        try:
            df_full = pd.read_excel(EXCEL_PATH, engine="openpyxl", header=0)
            cols_lower_full = {str(c).strip().lower(): c for c in df_full.columns}
            service_col = None
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

if 'status' not in df.columns:
    df['status'] = ""

print(f"Toplam {len(df)} hesap test edilecek")

# --------------------
# Tarayıcı ayarları
# --------------------
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Orijinal XPATH'ler (değişmedi)
XPATHS = {
    'email': "//input[@id='eMkroEmail']",
    'password': "//input[@id='eMkroPassword']",
    'login_button': "//span[contains(.,'Giriş Yap')]"
}

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

# --------------------
# Ana döngü
# --------------------
for index, row in df.iterrows():
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
        time.sleep(2)
        handle_popups(driver)
        driver.find_element(By.XPATH, XPATHS['email']).send_keys(username)
        driver.find_element(By.XPATH, XPATHS['password']).send_keys(password)
        driver.find_element(By.XPATH, XPATHS['login_button']).click()
        time.sleep(3)

        if any(keyword in driver.current_url.lower() or keyword in driver.page_source.lower() for keyword in ["anasayfa", "dashboard", "welcome"]):
            status = "200 - Başarılı Giriş"
            print(status)
            logging.info(status)
        else:
            error_elements = driver.find_elements(By.XPATH, "//*[contains(text(),'hatalı') or contains(text(),'yanlış')]")
            if error_elements:
                status = "404 - Kullanıcı/Şifre Hatalı"
                error_msg = error_elements[0].text[:50] + "..." if error_elements[0].text else ""
                print(f"{status} | Mesaj: {error_msg}")
                logging.warning(f"{status} | Mesaj: {error_msg}")
            else:
                status = "404 - Bilinmeyen Hata"
                print(status)
                logging.warning(status)

        df.at[index, 'status'] = status

    except Exception as e:
        error_msg = f"500 - Sistem Hatası: {str(e)[:100]}"
        print(error_msg)
        logging.error(error_msg)
        df.at[index, 'status'] = error_msg

# --------------------
# Temizlik ve sonuç kaydetme
# --------------------
driver.quit()
out_file = "login_results.xlsx"
df.to_excel(out_file, index=False)
print(f"\nTest tamamlandı! Sonuçlar: {out_file}")
