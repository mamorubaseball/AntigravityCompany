# A8.net Affiliate Manager Skill

This skill automates the management, categorization, and visualization of affiliate programs and links from A8.net.

## Quick Start

1. **Configure**: Create `config.json` in the project root (use `resources/config.json.example` as a template).
2. **Setup**: Ensure Python 3 and dependencies are installed.
3. **Automate**: Run the provided workflow to scrape, categorize, and update the dashboard.

## Features

- **Automated Scraping**: Periodically collects all approved programs and their tracking links.
- **Dynamic Categorization**: Groups programs into "投資", "エンジニア", and "その他" using a keyword-based engine.
- **Premium Dashboard**: A glassmorphic HTML interface (`dashboard.html`) for easy searching and one-click link copying.

## Operations

### End-to-End Update
Refer to the workflow at `.agent/workflows/update-dashboard.md` to refresh all data and the dashboard.

### Manual Collection
```bash
python3 scripts/a8_manager.py     # Scrape tracking URLs
python3 scripts/categorize_data.py # Categorize and update dashboard_data.js
```

## Directory Structure

- `.agent/`: Skill and workflow definitions.
- `scripts/`: Python automation scripts.
- `reports/`: Raw data and progress reports.
- `dashboard.html`: The human-friendly management interface.
- `dashboard_data.js`: The categorized data feeding the dashboard.
