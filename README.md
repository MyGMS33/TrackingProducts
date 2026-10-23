# TrackingProducts · MYGMS Price Intelligence Lab

Un véritable laboratoire personnel de suivi de prix **multi-produits** et **multi-vendeurs**, publié via GitHub Pages, puis déployable à l'identique sur Hermès (Linux). Les collectes fonctionnent sans modèle IA, sans token LLM et sans base cloud payante.

## Ce qui est inclus

- Interface responsive avec vue générale, catalogue filtrable, graphes interactifs (prix pratiqués / références barrées), comparaison des variantes, seuils personnels, diagnostic des collecteurs, export CSV.
- Catalogue déclaratif dans `config/products.json`. Un produit = un couple produit/vendeur. Utiliser le même `group_id` pour suivre un article chez plusieurs marchands.
- Trois moteurs d'extraction : `bultex_hyva` (10 dimensions Bultex en un chargement), `jsonld` (Product/Offer Schema.org) et `css` (sélecteurs statiques).
- Journal append-only `data/history.jsonl` ; prix en **centimes entiers** pour éviter les erreurs d'arrondi. Les échecs ne remplacent pas l'historique.
- Deux automatisations GitHub : collecte et publication Pages. Aucun secret Telegram sur le site public.
- Migration Hermès possible par timer systemd et Caddy.

## Installation sur le dépôt `MyGMS33/TrackingProducts`

1. Extraire l'archive **à la racine** de `TrackingProducts` (pas dans un sous-dossier). Garder les fichiers du dépôt existant en cas de conflit ; vérifier avant d'écraser.
2. Pousser sur la branche `main` :

   ```bash
   git clone https://github.com/MyGMS33/TrackingProducts.git
   cd TrackingProducts
   # Copier le contenu de l'archive ici.
   git add .
   git commit -m 'feat: laboratoire multi-produits tracking'
   git push origin main
   ```

3. Dans **Settings → Pages → Build and deployment**, sélectionner **GitHub Actions**.
4. Dans **Settings → Actions → General**, s'assurer que les permissions de workflow permettent les écritures du `GITHUB_TOKEN` (`Read and write permissions`) si nécessaire. Pour un dépôt avec protections de branche, adapter le mécanisme de commit.
5. Sous **Actions**, lancer manuellement **Relever les prix (sans IA)** (workflow_dispatch). Le premier relevé réussi alimente `data/history.jsonl`. Si Bultex refuse la connexion ou change ses scripts, l'échec est remonté dans `data/status.json` et les journaux ; aucun prix n'est inventé.
6. Le workflow **Publier le laboratoire GitHub Pages** produit une adresse sous la forme `https://MyGMS33.github.io/TrackingProducts/` après un premier déploiement réussi. La publication n'est pas effective tant que GitHub n'affiche pas une réussite.

### Rythme de collecte

Quatre événements cron UTC `07:15`, `08:15`, `19:15`, `20:15`, filtrés par la **vraie heure Europe/Paris** dans le code : un déclenchement autour de 09:15 et 21:15 après correction été/hiver. Les workflows GitHub peuvent être retardés/suspendus ; la précision horaire n'est pas garantie. Aucune requête supplémentaire ne doit être lancée pour essayer de contourner les protections anti-bot.

## Utilisation locale

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
python -m tracker.cli collect --dry-run  # Aucun fichier modifié
python -m tracker.cli collect            # Vrai relevé
python -m tracker.cli build              # Génère dist/
python -m http.server 8080 --directory dist
```

Ouvrir `http://localhost:8080` : le front-end ne dépend d'aucun backend applicatif. Ne pas ouvrir `web/index.html` directement avec `file://` (les fetch JSON seraient bloqués).

## Ajouter des produits

### Depuis l'interface

Cliquer sur **Ajouter un produit**. Renseigner le lien marchand, la marque, la catégorie et la méthode de relevé. L'interface télécharge une fiche JSON (et conserve un brouillon dans le navigateur) ; **le brouillon n'est pas publié ni collecté**. Intégrer cet objet dans le tableau `products` de `config/products.json`, créer un commit et attendre la publication.

### JSON-LD (cas simple)

```json
{
  "id": "produit-exemple-boutique",
  "group_id": "produit-exemple",
  "name": "Produit Exemple",
  "brand": "Marque",
  "seller": "Boutique Exemple",
  "category": "High-tech",
  "currency": "EUR",
  "url": "https://boutique-exemple.fr/produit",
  "adapter": "jsonld",
  "default_variant": "standard",
  "enabled": true,
  "alert_thresholds": { "standard": 99.90 }
}
```

Utiliser de **vraies URL accessibles**, pas celle de cet exemple. Cet adaptateur lit les balises JSON-LD Product/Offer. Certains marchands ne publient pas les prix en JSON-LD ou publient un prix différent du panier ; confirmer la qualité des résultats avant de s'y fier.

### Sélecteurs CSS (cas statique)

```json
{
  "id": "autre-produit-marchand",
  "group_id": "autre-produit",
  "name": "Autre produit",
  "brand": "Marque",
  "seller": "Marchand",
  "category": "Maison",
  "currency": "EUR",
  "url": "https://boutique-exemple.fr/un-autre-produit",
  "adapter": "css",
  "default_variant": "standard",
  "selectors": { "price": ".prix-reel", "reference": ".prix-barre" },
  "enabled": true
}
```

Les sélecteurs doivent être inspectés sur une vraie page. Les sites fortement dynamiques nécessitent un adaptateur Python dédié dans `tracker/adapters.py` puis l'ajout du nom dans `tracker/core.py`.

### Plusieurs marchands pour le même produit

Créer une entrée par marchand avec des `id` différents et un même `group_id` : cela prépare une comparaison inter-marchands sans mélanger leurs relevés. Les graphiques et le tableau actuel filtrent par source produit/vendeur. La conversion automatique entre devises n'est **pas** implémentée.

## Données et confidentialité

- `data/history.jsonl` : une ligne JSON par produit/variante/relevé, horodatage UTC ISO-8601. Les relevés sont publics si le dépôt est public.
- `data/status.json` : dernier contrôle, résultats ou erreurs par source.
- `data/alerts_sent.json` : état anti-duplication des alertes Telegram (aucune clé secrète).
- `dist/data/*.json` : vue catalogue et historique générée pour le navigateur ; les informations de scraping CSS internes ne sont pas publiées.
- **Le tableau ne doit jamais contenir de token Telegram, cookie marchand ou mot de passe**. Les seuils personnels du navigateur sont sauvegardés dans `localStorage` et ne notifient pas quand le site est fermé.

## Telegram (facultatif)

Dans GitHub **Settings → Secrets and variables → Actions**, créer les secrets `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`. Les seuils *automatiques* sont déclarés dans chaque produit via `alert_thresholds`. L'action Python envoie une notification à la première observation sous le seuil, puis n'en renvoie qu'après que le produit est repassé au-dessus. Pour les nouveaux minima, ajouter par exemple `"alert_new_lows": ["160x200"]` au produit ; seuls les minima *automatiquement constatés* sont pris en compte. Pas de secrets dans les journaux ou dans le site public.

## Hébergement Hermès

Sur Linux : cloner le dépôt dans `/opt/TrackingProducts`, configurer un venv et Chromium, activer `deploy/trackingproducts.service` et `deploy/trackingproducts.timer` après adaptation de `User=`/des chemins. Le service reconstruit `dist/` automatiquement après chaque collecte réussie. L'exemple `deploy/Caddyfile.example` sert `dist/` sous `prix.mygms.fr`. Pour préserver l'historique lors de la migration, exporter/copier `data/history.jsonl` et `data/status.json`, puis désactiver le workflow GitHub `track.yml` pour éviter deux collecteurs concurrents.

### Limites honnêtes

- Il faut respecter les CGU/robots applicables, ralentir les requêtes et ne pas contourner les défis CAPTCHA, authentifications ou autres protections. Certaines plateformes (TikTok Shop notamment) peuvent bloquer ce type de relevé ; les prix ne seront pas disponibles tant que la méthode n'aura pas été validée.
- Les références Bultex datant du 23 octobre 2026 sont incluses dans `historical_reference` **comme repères antérieurs non vérifiés par le nouveau collecteur** ; elles ne polluent pas `data/history.jsonl` ni les records/minima automatiques.
- Seuls les prix marchand constatés lors des relevés sont suivis ; frais de livraison, codes de réduction personnels, stocks en magasin et montant final du panier peuvent différer.
- Le tableau est un site statique public. Pour des données privées ou une édition serveur multi-utilisateur, il faudra ajouter une authentification et une API sur Hermès, hors du périmètre GitHub Pages.

Licence : usage personnel / expérimental, non affilié aux marchands suivis.
