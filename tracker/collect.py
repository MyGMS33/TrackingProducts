"""Collecte de prix Bultex sans LLM; historique public JSON append-only."""
import json
import os
import re
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "config/products.json"
HISTORY = ROOT / "data/history.json"
STATUS = ROOT / "data/status.json"

def save_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def bultex(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"], **({"channel": os.environ["TRACKING_CHROME_CHANNEL"]} if os.getenv("TRACKING_CHROME_CHANNEL") else {}))
        try:
            page = browser.new_page(locale="fr-FR", timezone_id="Europe/Paris")
            response = page.goto(url, wait_until="domcontentloaded", timeout=55000)
            if response is None or response.status >= 400:
                raise RuntimeError(f"HTTP {response.status if response else 'inconnu'}")
            page.wait_for_function("""() => {
              const el=document.querySelector('[x-data*="initConfigurableSwatchOptions"]');
              const state=el && window.Alpine && window.Alpine.$data(el);
              return state?.optionConfig?.attributes?.[300]?.options?.length>0 &&
                typeof state.getPriceFromOptionId==='function';
            }""", timeout=30000)
            return page.evaluate("""() => {
              const el=document.querySelector('[x-data*="initConfigurableSwatchOptions"]');
              const state=window.Alpine.$data(el);
              return state.optionConfig.attributes[300].options.map(o => {
                const p=state.getPriceFromOptionId(o.id);
                return {variant_id:String(o.label).toLowerCase().replace(/\\s+/g,'').replace(/×/g,'x'),
                  price:Number(p?.finalPrice?.amount),
                  reference_price:Number(p?.oldPrice?.amount),
                  available:state.optionIsEnabled?.(300,o.id) ?? true};
              });
            }""")
        finally:
            browser.close()


def parse_tractive_price(text):
    """Parse uniquement le prix du traceur (jamais les abonnements)."""
    pattern = (
        r"Prix\s+du\s+produit\s*"
        r"(?P<current>\d[\d\s.,]*)\s*€\s*"
        r"Prix\s+initial\s*"
        r"(?P<reference>\d[\d\s.,]*)\s*€"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        raise ValueError("Bloc tarifaire Tractive introuvable ou devise différente de EUR")
    def number(s):
        return Decimal(re.sub(r"[\s\u00a0\u202f]", "", s).replace(",", "."))
    current = number(match.group("current"))
    reference = number(match.group("reference"))
    if not (Decimal("5") <= current <= Decimal("999") and current <= reference <= Decimal("1999")):
        raise ValueError(f"Prix Tractive inattendu: {current}/{reference}")
    return current, reference


def tractive(url, variant):
    """La sélection est imposée dans l'URL; extraction du bloc prix du boîtier seul."""
    from urllib.parse import urlsplit, parse_qs
    from playwright.sync_api import sync_playwright
    parts = urlsplit(url)
    edition = parse_qs(parts.query).get("edition", [""])[0]
    country = parse_qs(parts.query).get("shopCountry", [""])[0]
    if parts.hostname != "tractive.com" or country != "FR" or edition not in (
        "xl-black", "xl-brown", "xl-adventure-orange"
    ):
        raise ValueError("URL Tractive non reconnue: pays France et édition obligatoire")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"], **({"channel": os.environ["TRACKING_CHROME_CHANNEL"]} if os.getenv("TRACKING_CHROME_CHANNEL") else {}))
        try:
            page = browser.new_page(locale="fr-FR", timezone_id="Europe/Paris")
            response = page.goto(url, wait_until="domcontentloaded", timeout=55000)
            if response is None or response.status >= 400:
                raise RuntimeError(f"Tractive HTTP {response.status if response else 'inconnu'}")
            page.wait_for_function("""() => /Prix du produit/i.test(document.querySelector("main")?.textContent || "")""", timeout=30000)
            texts = page.locator("main p").all_text_contents()
            texts.append(page.locator("main").text_content(timeout=10000) or "")
            failure = None
            for t in texts:
                try:
                    val, ref = parse_tractive_price(t)
                    return {
                        "variant_id": variant, "price": float(val),
                        "reference_price": float(ref), "available": None, "url": url,
                    }
                except ValueError as exc:
                    failure = exc
            raise ValueError(f"Impossible d'isoler le prix EUR du {variant}: {failure}")
        finally:
            browser.close()



def parse_soundboks_shopify(data, expected_product_id, variant_ids):
    """Price the exact new SOUNDBOKS 4 Shopify product from EUR cent values."""
    if not isinstance(data, dict) or data.get("id") != expected_product_id:
        raise ValueError("Wrong SOUNDBOKS 4 Shopify product ID")
    if data.get("handle") != "soundboks-4":
        raise ValueError("Wrong SOUNDBOKS product handle")
    if "soundboks 4" not in str(data.get("title", "")).casefold():
        raise ValueError("Unexpected SOUNDBOKS product title")
    raw_variants = data.get("variants")
    if not isinstance(raw_variants, list):
        raise ValueError("No Shopify variants")
    found = []
    for label, expected_id in variant_ids.items():
        matches = [v for v in raw_variants if isinstance(v, dict) and v.get("id") == expected_id]
        if len(matches) != 1:
            raise ValueError("Missing or duplicated SOUNDBOKS variant " + label)
        v = matches[0]
        if v.get("option1") != label:
            raise ValueError("Shopify variant label changed for " + label)
        cents = v.get("price")
        compare_cents = v.get("compare_at_price")
        if isinstance(cents, bool) or not isinstance(cents, int) or not 20000 <= cents <= 200000:
            raise ValueError("Invalid SOUNDBOKS selling price for " + label)
        if compare_cents is not None:
            if (isinstance(compare_cents, bool) or not isinstance(compare_cents, int)
                    or compare_cents < cents or compare_cents > 250000):
                raise ValueError("Incoherent SOUNDBOKS comparison price for " + label)
        available = v.get("available")
        if not isinstance(available, bool):
            raise ValueError("Unknown SOUNDBOKS stock for " + label)
        found.append({
            "variant_id": label, "price": cents / 100,
            "reference_price": compare_cents / 100 if compare_cents is not None else None,
            "available": available
        })
    return found


def soundboks_shopify(product):
    """Single official Shopify JSON request obtains both grille colors."""
    from urllib.request import Request, urlopen
    from urllib.parse import urlsplit
    url = product["url"]
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "soundboks.eu" or
            parsed.path != "/fr/products/soundboks-4" or parsed.query):
        raise ValueError("Unsupported SOUNDBOKS product URL")
    json_url = url + ".js"
    request = Request(json_url, headers={
        "Accept": "application/json",
        "User-Agent": "TrackingProducts personal price tracker (+https://github.com/MyGMS33/TrackingProducts)"
    })
    with urlopen(request, timeout=40) as response:
        if response.status != 200:
            raise RuntimeError(f"SOUNDBOKS Shopify HTTP {response.status}")
        raw = response.read(1000000)
        if len(raw) >= 1000000:
            raise ValueError("SOUNDBOKS Shopify JSON response too large")
    data = json.loads(raw)
    variants = parse_soundboks_shopify(data, product["product_id"], product["variant_ids"])
    for variant in variants:
        variant["url"] = url
    return variants


def collect():
    products=json.loads(CATALOG.read_text(encoding="utf-8"))["products"]
    hist=json.loads(HISTORY.read_text(encoding="utf-8"))
    status=json.loads(STATUS.read_text(encoding="utf-8"))
    stamp=datetime.now(timezone.utc).isoformat()
    status["last_run"]=stamp
    status.setdefault("sources",{})
    errors=[]
    changed=False
    for product in products:
        if not product.get("enabled",True):continue
        pid=product["id"]
        try:
            if product["adapter"] == "bultex_hyva":
                result = bultex(product["url"])
            elif product["adapter"] == "tractive_dog6":
                urls = product["variant_urls"]
                if set(urls) != set(product["expected_variants"]):
                    raise ValueError("Variantes et URLs Tractive incohérentes")
                result = [tractive(urls[name], name) for name in product["expected_variants"]]
            elif product["adapter"] == "soundboks_shopify":
                result = soundboks_shopify(product)
            else:
                raise ValueError("Adaptateur non pris en charge : "+product["adapter"])
            expected=set(product["expected_variants"])
            actual={row["variant_id"] for row in result}
            if actual!=expected or len(result)!=len(expected):
                raise ValueError(f"Variantes incorrectes: attendues={sorted(expected)} reçues={sorted(actual)}")
            rows=[]
            for row in result:
                val=row["price"]; ref=row["reference_price"]
                if not isinstance(val,(int,float)) or not (0 < val < 100000):
                    raise ValueError(f"Prix absents ou invalides pour {row['variant_id']}")
                if ref is None:
                    if product["adapter"] != "soundboks_shopify":
                        raise ValueError(f"Prix de référence manquant pour {row['variant_id']}")
                elif not isinstance(ref,(int,float)) or not (val <= ref < 100000):
                    raise ValueError(f"Prix barré incohérent pour {row['variant_id']}")
                rows.append({"observed_at":stamp,"product_id":pid,"variant_id":row["variant_id"],
                    "price_cents":round(val*100),"reference_cents":round(ref*100) if ref is not None else None,
                    "currency":product.get("currency","EUR"),"source":row.get("url", product["url"]),"available":row["available"]})
            hist["observations"].extend(rows)
            changed=True
            status["sources"][pid]={"status":"ok","checked_at":stamp,"variants":len(rows)}
            print(f"OK {pid}: {len(rows)} variantes")
        except Exception as exc:
            status["sources"][pid]={"status":"error","checked_at":stamp,"error":str(exc)[:400]}
            errors.append(pid)
            print(f"ERREUR {pid}: {exc}",flush=True)
    if changed:save_json(HISTORY,hist)
    save_json(STATUS,status)
    if errors:raise SystemExit(1)

if __name__=="__main__":
    collect()
