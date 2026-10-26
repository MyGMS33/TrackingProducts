# SOUNDBOKS 4 - suivi du prix neuf

Site officiel : https://soundboks.eu/fr/products/soundboks-4

Source JSON publique Shopify : https://soundboks.eu/fr/products/soundboks-4.js

Le suivi conserve deux variantes : Noir (47078090506565) et Gris Métallique (47078090670405). L'ID du produit est 8660358791493.

Seul le prix de l'enceinte neuve en EUR est relevé. Les modèles reconditionnés, batteries séparées, chargeurs et autres packs ne sont pas suivis. La batterie est incluse, le chargeur USB-C n'est pas inclus.

Lorsque Shopify ne publie pas de compare_at_price, le prix de référence reste null : aucun faux prix barré n'est créé. Chaque valeur est contrôlée avant d'entrer dans l'historique. Une variante manquante fait échouer le produit sans historique incomplet. Le prix et l'état de stock peuvent évoluer indépendamment.

Une requête HTTP JSON suffit pour les deux variantes ; aucun navigateur ni IA n'est nécessaire pour ce collecteur. Tests : python -m unittest discover -s tests -v.
