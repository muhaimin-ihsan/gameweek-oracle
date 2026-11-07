# Gameweek Oracle

An FPL (Fantasy Premier League) predictor for the next gameweek. It reads live data from the official FPL API, rates every team and player, and estimates who is most likely to score well. The output is a single web page you can open in any browser.

![Gameweek Oracle screenshot](docs/screenshot.png)
<!-- Add a screenshot at docs/screenshot.png (the hero or the Oracle XI pitch works best). -->

**Live demo:** [Gameweek-Oracle](https://muhaimin-ihsan.github.io/gameweek-oracle/gameweek-oracle.html)

## Features

- **Gameweek recap**: last gameweek's results with scorers and expected goals (xG), the league table with form, top scorers, owned flops and the players in the best form.
- **Fixture predictions**: win, draw and loss chances, expected goals, clean sheet chances and a 1–5 difficulty rating for every match.
- **Oracle XI**: the highest expected-points eleven in a legal FPL formation (max 3 per club), with a captain pick. Each slot has the 2nd and 3rd best options.
- **Player of the week odds**: how often each player finishes as the top FPL scorer across thousands of simulated gameweeks.
- **Squad builder**: pick a club, then a player, for each position. It shows your chance to beat the average manager, your chance to beat the Oracle XI, and checks the budget, the 3-per-club rule and injury doubts.
- **Saved squads**: save named combinations and compare them before the deadline. On GitHub Pages they are kept in your browser.
- **Player table**: every player, sortable by expected points, 6+ point chance, form, price and value.
- **Live match in the background**: an endless simulated match between the real fixtures and real lineups. It has marking, fouls, goal kicks and substitutions at stoppages. Press **Watch** to view it full screen.

## How the predictions work

| Step | What it does |
| --- | --- |
| Team strength | Attack and defence ratings from goals and xG in every gameweek so far. Recent weeks count more, and small samples are pulled toward the league average. |
| Fixture | Expected goals = league average × own attack × opponent defence, about +12% at home. Clean sheet chance = chance the opponent scores 0. |
| Minutes | Recent and season minutes plus FPL's injury flags give the chance a player starts and reaches 60 minutes. |
| Points | xG and expected assists per 90 minutes, scaled by the fixture, are converted with the official FPL scoring: goals, assists, clean sheets, goals conceded, saves, defensive contributions, bonus and cards. |
| Form | About 28% of each forecast comes from points per appearance over the last 5 gameweeks, adjusted for the fixture. |
| Simulation | Players and matches are simulated thousands of times (Poisson goals, shared results per club) to get the percentages. |

These are estimates for fun, not betting or financial advice.

## Project structure

```
gameweek-oracle/
├── gameweek-oracle.html   # the built page (open this, or serve it)
├── README.md
└── src/
    ├── refresh.sh         # downloads fresh FPL data and rebuilds everything
    ├── build_data.py      # team ratings, player forecasts -> data.json
    ├── assemble.py        # puts data.json into template.html -> gameweek-oracle.html
    ├── template.html      # page layout, styles and all the JavaScript
    └── data.json          # model output for the current gameweek
```

## Getting started

Requirements: Python 3.9+ and `curl`. On Windows, run the shell script from Git Bash. No Python packages are needed.

Open the page that is already built:

```bash
python -m http.server 8000
```

Then go to http://localhost:8000/gameweek-oracle.html.

Update it for the next gameweek. Run this after the current gameweek has finished and before the next deadline:

```bash
bash src/refresh.sh
```

This downloads the FPL data (`bootstrap-static`, `fixtures` and each gameweek's `live` endpoint), runs the model and rebuilds `gameweek-oracle.html`.

## Deploying to GitHub Pages

1. Push the repository to GitHub.
2. Go to **Settings → Pages** and set the source to the `main` branch, root folder.
3. Rename `gameweek-oracle.html` to `index.html`, or link to it directly at `https://<user>.github.io/<repo>/gameweek-oracle.html`.

## Data source

All data comes from the public Fantasy Premier League API (`https://fantasy.premierleague.com/api/`). It has no official documentation and can change without notice. Please don't call it more often than you need to.

## Roadmap ideas

- [ ] Run the refresh automatically each week with GitHub Actions
- [ ] Load your own FPL team by team ID
- [ ] Transfer suggestions within a budget
- [ ] Forecasts for several gameweeks ahead

## Disclaimer

Gameweek Oracle is an independent fan project. It is not affiliated with or endorsed by the Premier League or Fantasy Premier League. Club names belong to their owners.

## License

MIT. Add a `LICENSE` file if you use it.
