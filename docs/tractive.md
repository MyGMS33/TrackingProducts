# Tractive DOG 6 XL / XL Adventure

Suivi du **prix du traceur seul, hors abonnement** chez Tractive, livraison France (shopCountry=FR).

- DOG 6 XL : Noir et Marron, sélections `xl-black` et `xl-brown`
- DOG 6 XL Adventure : Orange, sélection `xl-adventure-orange`
- Le script exige que la devise affichée soit l'euro, que les prix de vente et de référence soient identifiés dans le bloc "Prix du produit / Prix initial", et rejette un tarif mensuel d'abonnement.
- Un produit échoué ne produit **aucun faux relevé** pour ses variantes ; son erreur est stockée dans `data/status.json`.
- Les produits/variantes sont déclarés dans `config/products.json`. Les historiques sont indépendants et interrogeables dans `data/history.json`.
- Tests du parseur : `python -m unittest discover -s tests -v`.
- Les prix peuvent varier selon la localisation, la promotion, la session ou le stock. Une page inaccessible laisse le dernier prix connu et une erreur explicite.

**Important :** les contrôles automatisés doivent respecter les conditions applicables au site Tractive. Ne pas contourner les CAPTCHA ni les restrictions d'accès.
