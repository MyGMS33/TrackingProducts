import unittest
from decimal import Decimal
from tracker.collect import parse_tractive_price


class TractiveParserTests(unittest.TestCase):
    def test_regular_price(self):
        self.assertEqual(parse_tractive_price("Prix du produit 79 € Prix initial 79 €"),
                         (Decimal("79"), Decimal("79")))

    def test_promotion_fr(self):
        self.assertEqual(parse_tractive_price("Prix du produit 59,40 € Prix initial 99 €"),
                         (Decimal("59.40"), Decimal("99")))

    def test_nbsp(self):
        self.assertEqual(parse_tractive_price("Prix du produit 79\u00a0€ Prix initial 79\u00a0€"),
                         (Decimal("79"), Decimal("79")))

    def test_no_subscriptions(self):
        with self.assertRaises(ValueError):
            parse_tractive_price("À partir de 5 €/mois Paiement de 120 € tous les 2 ans")

    def test_usd_rejected(self):
        with self.assertRaises(ValueError):
            parse_tractive_price("Prix du produit $79 Prix initial $79")


if __name__ == "__main__":
    unittest.main()
