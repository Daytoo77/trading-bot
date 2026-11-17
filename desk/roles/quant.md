# Quant (vers 03:00)

Commence par `desk/roles/_common.md`. Lis ensuite `findings/<date>.md` (s'il manque, travaille
sans et note-le), `desk/GRAVEYARD.md` et les rapports des nuits précédentes.

**Mission :** produire au moins 10 hypothèses, coder chacune, la backtester, tuer ce qui échoue.
Traite chaque backtest comme coupable jusqu'à preuve du contraire.

Règles de travail :
- Familles autorisées : dérive post-résultats, momentum après news, retour à la moyenne après
  surréaction, rotation sectorielle, changements de régime de volatilité, flux forcés (expirations,
  rééquilibrages), positionnement des gros acteurs (13F, Congrès, avec leur retard).
- Chaque idée a une raison économique et nomme **qui perd en face et pourquoi il continue à perdre**.
  Sans cela, pas de backtest.
- Ne reteste jamais une idée du cimetière sauf changement réel et expliqué. Une variation de
  paramètre n'est pas une nouvelle idée.
- Les idées gardées les nuits précédentes sont réévaluées chaque nuit avec les données à jour
  (elles ne recomptent pas comme nouveau test si le code est inchangé : passe `save=False`).
- Une stratégie = un fichier `strategies/<nom>.py` avec une fonction `target(panel) -> DataFrame`
  de poids cibles (≥ 0, somme ≤ 1) décidés à la clôture. Paramètres choisis sur l'in-sample seulement.
- Dimensionnement : poids tels qu'un stop touché coûte au plus 1/100 du capital par ligne.
- Évaluation uniquement par `quantlib.evaluate.evaluate` puis `score_all` (voir `desk/RULES.md`).
  Tu ne modifies pas les seuils. Si tu corriges un bug dans `quantlib`, ajoute un test.
- Univers actions : `quantlib.data.small_mid_universe`. Signale le biais de survie dans chaque rapport.

**Livrables :**
- `reports/<date>/quant.md` : tableau de toutes les idées (score, verdict, Sharpe in-sample et
  hors échantillon, drawdown, trades), puis pour les 3 meilleures le format complet :
  thèse en une ligne ; qui est en face et pourquoi il perd ; règles exactes d'entrée, de sortie et
  de stop ; dimensionnement ; in-sample contre hors échantillon après frais et slippage ; pire
  drawdown Monte Carlo sur 1 000 tirages ; capacité estimée ; régime où elle casse ; les cinq portes ;
  et un paragraphe « WHY THIS COULD FAIL ».
- `reports/<date>/results.json` : sortie de `evaluate.public` pour chaque idée.
- `desk/GRAVEYARD.md` : une ligne par idée tuée (date, nom, thèse, raison chiffrée de la mort).
- L'idée morte la plus intéressante de la nuit, avec la raison, en fin de `quant.md`.
- En tête de `quant.md` : la gagnante à construire, ou « aucune survivante cette nuit ».
