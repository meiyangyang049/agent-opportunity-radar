# Agent Opportunity Radar

An AI-assisted early-signal radar for detecting emerging agent products that may become high-value Kimi API customers, ecosystem partners, or strategically relevant competitors.

The prototype combines public developer signals and product/news signals, applies a deterministic commercial score, optionally asks Kimi to refine the judgment, and publishes a static sales-ready dashboard.

## Business question

> Can a model provider detect the next OpenClaw-like open-source ecosystem or Manus-like commercial agent before it becomes obvious to the broader market?

The radar is designed for Kimi API commercial, sales operations, and ecosystem teams. It prioritizes actionability over generic popularity: every recommended candidate includes evidence, an opportunity type, a commercial interpretation, and a suggested sales action.

## Signal coverage

| Source | Primary signal | Opportunity archetype |
| --- | --- | --- |
| GitHub | New repositories, stars, forks, issues, topics | OpenClaw-like |
| Hacker News | Early developer discussion, points, comments | Both |
| Product Hunt | Product launches and positioning | Manus-like |
| AI news RSS | Launch, funding, pricing, partnership signals | Manus-like |

## Scoring model

| Dimension | Weight |
| --- | ---: |
| Growth speed | 25% |
| Agent innovation | 20% |
| Community and user signal | 20% |
| API consumption potential | 15% |
| Commercial maturity | 10% |
| Kimi strategic fit | 10% |

Rules create an auditable pre-score. When `MOONSHOT_API_KEY` is available, Kimi evaluates the strongest candidates, adjusts the score within a bounded range, classifies the opportunity, and writes a concise reason to act. Kimi is not allowed to invent revenue, funding, users, or partnerships.

## Quick start

Python 3.10+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --demo --no-kimi
```

Open `docs/index.html` directly in a browser. Demo mode uses clearly labelled historical calibration and illustrative data, never disguised as live intelligence.

### Run with public live signals

```bash
python -m src.main --no-kimi
```

### Add Kimi judgment

Create an API key in Kimi API Platform and expose it as an environment variable. Never commit it.

```bash
export MOONSHOT_API_KEY="your-key"
python -m src.main
```

The default model is configurable in `config.yaml` and currently set to `kimi-k2.6` with thinking disabled for a lightweight scoring pass.

## Outputs

- `data/candidates.json`: latest structured result
- `data/history.csv`: cross-run history for future velocity analysis
- `docs/index.html`: self-contained static dashboard
- `data/raw/latest.json`: latest raw collector output, ignored by Git

## GitHub Actions and Pages

The workflow at `.github/workflows/daily-radar.yml` runs every day at 09:00 Asia/Shanghai and can also be started manually.

1. Add a repository secret named `MOONSHOT_API_KEY`.
2. In **Settings → Pages**, select **GitHub Actions** as the publishing source.
3. In **Actions**, run **Daily Agent Radar** manually for the first deployment.

GitHub provides `GITHUB_TOKEN` automatically. The workflow runs tests, refreshes the radar, commits the public outputs, and deploys `docs/` to GitHub Pages.

## Responsible interpretation

The score is a prioritization aid, not a prediction of future success. Early public signals are noisy and can be manipulated. High-scoring candidates still require a human to verify the company, team, model stack, commercial status, contact path, and legal/compliance considerations before CRM creation or outreach.

