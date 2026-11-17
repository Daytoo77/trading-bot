# Démarrage commun à tous les agents

1. Travaille dans le checkout de `Daytoo77/trading-bot`. S'il est absent, attache le dépôt avec
   l'outil `add_repo` (owner `Daytoo77`, repo `trading-bot`, accès `push`), clone-le, puis
   `git pull` sur `main`.
2. Lis `desk/RULES.md` en entier. Ces règles priment.
3. `pip install -r requirements.txt`, puis `python3 -m pytest -q`. Si un test échoue, répare
   d'abord ou arrête-toi en le signalant dans `desk/HANDOFFS.md`.
4. La « date du desk » est la date du jour à Zurich (`TZ=Europe/Zurich date +%F`).
5. En fin de tâche : ajoute une ligne à `desk/HANDOFFS.md`
   (`date heure | agent | ce qui est livré | fichier | ce qui manque`), commit, puis
   `git push origin main` (si le push est refusé : `git pull --rebase origin main`, puis repousse).
6. Tu n'as personne à qui poser de question pendant la nuit. Si tu es bloqué, note une seule
   question dans `reports/<date>/questions.md` et continue avec le reste.
7. Un hôte réseau refusé n'est pas une raison d'inventer : note la source comme indisponible.
   Sources ouvertes : Yahoo Finance (query1/query2), SEC EDGAR (data.sec.gov, www.sec.gov, avec un
   User-Agent descriptif), Coinbase Exchange, Kraken, api.nasdaq.com, nasdaqtrader.com,
   disclosures-clerk.house.gov, Alpaca. Pour les news et la macro, utilise la recherche web.
