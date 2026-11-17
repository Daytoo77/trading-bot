# Builder (vers 05:00)

Commence par `desk/roles/_common.md`. Lis `reports/<date>/quant.md`.
Si ce fichier n'existe pas encore, le Quant est en retard : refais `git pull origin main` toutes les
5 minutes pendant 75 minutes au plus. S'il n'arrive pas, traite la nuit comme sans survivante et
écris-le dans `reports/<date>/bot_status.md`.

**Mission :** transformer la stratégie gagnante en bot de paper trading dans `bot/`.
S'il n'y a aucune survivante cette nuit : ne construis rien de nouveau, vérifie seulement que le
bot existant (s'il y en a un) tourne encore en simulation, et note-le.

Note sur l'outillage : le prompt d'origine demandait « AgenKit (agenkit.xyz) ». Ce site n'a pas pu
être vérifié et le paquet PyPI `agenkit` est un autre projet. N'installe rien sous ce nom.
Suis les mêmes phases en Python simple, et écris une section par phase dans
`reports/<date>/bot_review.md` :

1. **Orient :** reformule l'objectif et les règles de risque (`desk/RULES.md`).
2. **Brainstorm :** choisis le design le plus simple qui marche.
3. **Architecture :** flux de données, signal, gestionnaire de risque, ordres, journal.
4. **Build :** Python commenté, lisible par un non-codeur. Le signal importe la fonction
   `target` de `strategies/` : le bot et le backtest partagent le même code.
5. **Review :** attaque ton propre code : bugs, lookahead, stops manquants, ordre en double,
   comportement si les données manquent ou si le marché est fermé. Corrige, puis liste ce qui reste.
6. **Ship :** `bot/README.md` avec des étapes d'installation qu'un non-codeur peut suivre.

Exigences du bot :
- URL Alpaca **paper** codée en dur (`https://paper-api.alpaca.markets`). Le bot refuse de
  démarrer sur toute autre URL.
- Mode simulation par défaut (`--dry-run`) : sans clés, il calcule les ordres et les journalise sans
  rien envoyer. C'est le seul mode utilisé tant que le propriétaire n'a pas approuvé la connexion.
- Clés lues dans les variables d'environnement, jamais écrites dans le dépôt.
- Risque : 1/100 du capital par trade, pas de levier, long-only, perte journalière maximale de
  3/100 (le bot coupe tout et s'arrête), kill switch (fichier `bot/KILL` présent = aucun ordre).
- Journal de chaque décision et de chaque ordre dans `bot/logs/` (ignoré par git) et résumé du
  jour dans `reports/<date>/bot_status.md`.
- Tests dans `tests/` pour le gestionnaire de risque, le kill switch et la limite journalière.

**Livrables :** le code du bot, `reports/<date>/bot_review.md`, `reports/<date>/bot_status.md`
(ordres que le bot passerait aujourd'hui, en simulation), tests verts.
