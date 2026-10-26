import unittest
from tracker.collect import parse_soundboks_shopify

PID = 8660358791493
IDS = {"Noir": 47078090506565, "Gris Métallique": 47078090670405}


def fixture():
    return {
        "id": PID, "handle": "soundboks-4", "title": "Soundboks 4",
        "variants": [
            {"id": IDS["Noir"], "option1": "Noir", "price": 99900,
             "compare_at_price": None, "available": True},
            {"id": IDS["Gris Métallique"], "option1": "Gris Métallique",
             "price": 99900, "compare_at_price": None, "available": True},
        ]
    }


class SoundboksPriceTests(unittest.TestCase):
    def test_two_versions_without_fake_reference(self):
        out = parse_soundboks_shopify(fixture(), PID, IDS)
        self.assertEqual([r["variant_id"] for r in out], ["Noir", "Gris Métallique"])
        self.assertEqual([r["price"] for r in out], [999.0, 999.0])
        self.assertTrue(all(r["reference_price"] is None for r in out))

    def test_sale_and_stock(self):
        doc = fixture()
        doc["variants"][0]["price"] = 84900
        doc["variants"][0]["compare_at_price"] = 99900
        doc["variants"][0]["available"] = False
        row = parse_soundboks_shopify(doc, PID, IDS)[0]
        self.assertEqual(row["price"], 849.0)
        self.assertEqual(row["reference_price"], 999.0)
        self.assertFalse(row["available"])

    def test_missing_variant_rejected(self):
        doc = fixture()
        del doc["variants"][1]
        with self.assertRaises(ValueError):
            parse_soundboks_shopify(doc, PID, IDS)

    def test_wrong_product_rejected(self):
        doc = fixture()
        doc["id"] = 123
        with self.assertRaises(ValueError):
            parse_soundboks_shopify(doc, PID, IDS)

    def test_bad_compare_price_rejected(self):
        doc = fixture()
        doc["variants"][0]["compare_at_price"] = 89900
        with self.assertRaises(ValueError):
            parse_soundboks_shopify(doc, PID, IDS)


if __name__ == "__main__":
    unittest.main()
