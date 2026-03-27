# How the Hazina Listing Scanner Works

## Official NSE Requirements (Verified Source)

**Source:** [NSE Guide to Listing PDF](https://www.nse.co.ke/wp-content/uploads/guide-to-listing-2.pdf)

| Segment | Share Capital | Net Assets | Shareholders | Free Float | Trading/Profits |
|---------|--------------|------------|--------------|------------|-----------------|
| **GEMS** | KES 10M | — | 15% to public | 15% | 2 years (1 profit) |
| **AIMS** | KES 20M | KES 20M | 100 (20%) | 20% | 2 years (1 profit) |
| **MIMS** | KES 50M | KES 100M | 1,000 (25%) | 25% | 3 of 5 years profit |

---

## Data Sources Explained

### 1. User Input (70% of scoring)
- Company information, financials, board members
- Documents ready, key parties appointed
- Self-reported data

### 2. Public Verification (20% of scoring)
- **Business Daily Africa RSS** - Scraped for company mentions
- **The Star Kenya** - Scraped for news and red flags
- Looks for: fine, lawsuit, tax, fraud, scandal, investigation

### 3. NSE Rules (10% of scoring)
- **Official Source:** NSE Guide to Listing PDF
- Hardcoded segment requirements (GEMS/AIMS/MIMS)
- Board governance rules (5 directors, 1/3 independent)

---

## How Each Dimension Is Scored

| Dimension | Calculation | Data Source |
|-----------|-------------|-------------|
| **Revenue** | CAGR from revenue_history → 0-10 score | User input |
| **Governance** | Board count + independence % → 0-10 score | User input |
| **Growth** | Revenue score × sector multiplier | User input |
| **Compliance** | Tax status - penalties for red flags | User input + News |
| **Market Size** | Pre-defined sector score | User's sector |
| **Timing** | Fixed 6/10 (TODO: integrate sentiment) | N/A |

---

## Key Takeaways for Your Boss

1. **NSE requirements are public** — we used the official NSE Guide to Listing PDF
2. **70% is rule-based** — scoring formulas on user input
3. **30% is verification** — news scraping for red flags
4. **No insider data** — everything is publicly available
5. **Not financial advice** — this is a screening tool, not investment advice
