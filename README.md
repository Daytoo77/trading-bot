# trading-bot : desk quant de nuit (paper trading uniquement)

Trois agents tournent chaque nuit, cherchent des stratégies, les soumettent à des tests durs
et transforment la meilleure en bot de paper trading. Aucun argent réel n'est engagé.

| Heure (Zurich) | Agent | Fiche de rôle | Sortie |
|---|---|---|---|
| ~01:00 | Scout | `desk/roles/scout.md` | `findings/AAAA-MM-JJ.md` |
| ~03:00 | Quant | `desk/roles/quant.md` | `reports/AAAA-MM-JJ/`, `strategies/`, `desk/GRAVEYARD.md` |
| ~05:00 | Builder | `desk/roles/builder.md` | `bot/`, `reports/AAAA-MM-JJ/bot_review.md` |
| ~07:30 | Brief | `desk/roles/brief.md` | `reports/AAAA-MM-JJ/brief.md` + message |
| dimanche | Hebdo | `desk/roles/weekly.md` | `reports/weekly/AAAA-MM-JJ.md` |

- `desk/RULES.md` : les règles du desk. Elles priment sur tout le reste.
- `desk/HANDOFFS.md` : journal des passages de relais entre agents.
- `desk/GRAVEYARD.md` : idées tuées, pour ne jamais les retester par accident.
- `desk/trials.json` : compteur de toutes les idées testées, utilisé par le Sharpe déflaté.
- `quantlib/` : chargement des données, backtest sans lookahead, statistiques, score sur 25.

```bash
pip install -r requirements.txt
```

```bash
python3 -m pytest -q
```

Rien ici n'est un conseil financier. Un backtest ne garantit aucun gain futur.
