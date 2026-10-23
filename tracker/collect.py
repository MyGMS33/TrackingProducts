"""Collecte de prix Bultex sans LLM; historique public JSON append-only."""
import json
import os
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
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
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
            if product["adapter"]!="bultex_hyva":raise ValueError("Adaptateur non pris en charge : "+product["adapter"])
            result=bultex(product["url"])
            expected=set(product["expected_variants"])
            actual={row["variant_id"] for row in result}
            if actual!=expected or len(result)!=len(expected):
                raise ValueError(f"Variantes incorrectes: attendues={sorted(expected)} reçues={sorted(actual)}")
            rows=[]
            for row in result:
                val=row["price"]; ref=row["reference_price"]
                if not isinstance(val,(int,float)) or not (0 < val < 100000) or not isinstance(ref,(int,float)) or not (0 < ref < 100000):
                    raise ValueError(f"Prix absents ou invalides pour {row['variant_id']}")
                rows.append({"observed_at":stamp,"product_id":pid,"variant_id":row["variant_id"],
                    "price_cents":round(val*100),"reference_cents":round(ref*100),
                    "currency":product.get("currency","EUR"),"source":product["url"],"available":row["available"]})
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
