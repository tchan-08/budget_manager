# Personal Finance Manager

A desktop personal finance manager built with **PyQt5**, **SQLite**, and **matplotlib**. It tracks income, expenses, and savings; supports financial goals with prerequisite chains and priorities; automates recurring payments; and provides algorithm-driven budget allocation and predictive analytics.

## Features

- **Balance & Savings Tracking** — Maintain a main balance and a separate savings balance, with deposit/withdraw support and full transaction history.
- **Goals**
  - Create goals with a target amount, deadline, and priority (LOW / MEDIUM / HIGH).
  - Link goals into prerequisite chains (parent/child relationships), with circular-dependency protection.
  - View chain cost, root goal, and child goals for any goal.
  - Track progress visually via a per-goal progress bar.
- **Recurring Payments** — Define recurring income or expenses (daily, weekly, or monthly) and automatically apply due items to the balance.
- **Automated Budget Allocation** — Allocate available funds across goals using either:
  - **0/1 Knapsack** (`Goal_Allocator.allocate_budget`) — optimal allocation based on goal priority as "value" and target cost as "weight".
  - **Greedy** (`Goal_Allocator.greedy`) — priority-sorted allocation (via a custom quicksort) that spreads remaining budget across unmet goals.
- **Predictive Analytics**
  - Weighted moving-average predictions for future income, expenses, and savings (`Predictor.weighted_predictions`).
  - Monte Carlo simulation to estimate the probability of hitting a goal's target by its deadline (`Predictor.monte_carlo`).
  - Goal scoring/classification (Good / Okay / Bad) combining progress, time remaining, available funds, and simulated success probability.
- **Graphs & Statistics** — Expense distribution (pie chart), income trend with linear regression forecast, and goal progress (current vs. predicted) via `matplotlib`.
- **Status Export** — Download a snapshot of balance, expenses, and recurring items as a CSV/text file.
- **Persistent Storage** — All data (balance, goals, transactions, recurring items) is stored in a local SQLite database (`database.db`).

## Project Structure

| File | Description |
|---|---|
| `main.py` | Application entry point. Defines the PyQt5 GUI: main window, goal/recurring/allocator/graph dialogs, and all user interaction logic. |
| `udt.py` | Core data model: `Goal`, `Transaction`, `Recurring_Item`, `Budget_Report`, `Goal_Node`, `Stack`, and the `Transaction_Type` / `Priority_Type` / `Chain_Status` enums. Handles loading/saving records to SQLite. |
| `algorithms.py` | `Goal_Allocator` (knapsack and greedy budget allocation, quicksort by priority) and `Predictor` (weighted predictions, Monte Carlo simulation, goal classification). |
| `db_setup.py` | One-time setup script that creates the SQLite schema: `Info`, `Goals`, `Recurring_Items`, and `Transactions` tables. |

## Requirements

- Python 3
- [PyQt5](https://pypi.org/project/PyQt5/)
- [matplotlib](https://pypi.org/project/matplotlib/)
- [numpy](https://pypi.org/project/numpy/)

Install dependencies:

```bash
pip install PyQt5 matplotlib numpy
```

## Setup & Usage

1. **Create the database** (run once, or whenever you need a fresh database):
   ```bash
   python db_setup.py
   ```
   This creates `database.db` in the project directory with the required tables.

2. **Launch the application**:
   ```bash
   python main.py
   ```

3. From the main window you can:
   - Add and manage goals, including setting prerequisites and priorities.
   - Set up recurring income/expenses and apply due items.
   - Set your current balance and move money to/from savings.
   - Run automatic budget allocation (knapsack or greedy).
   - View graphs and predictive analytics.
   - Export your current status to a file.

## How the Algorithms Work

- **Knapsack allocation** treats each goal's remaining cost as a "weight" and its priority as a "value," building a DP table to select the combination of goals that maximizes total priority within the available budget, then distributes funds accordingly.
- **Greedy allocation** sorts goals by priority (highest first) using a custom quicksort, then repeatedly splits the remaining budget evenly across unfinished goals until funds run out or all goals are complete.
- **Weighted predictions** apply a fixed set of weights (`[0.4, 0.25, 0.15, 0.12, 0.08]`) to the five most recent transactions (via a `Stack`) to forecast near-term income, expenses, and savings.
- **Monte Carlo simulation** runs many simulated trials of monthly savings (drawn from a normal distribution fitted to historical data) to estimate the probability of a goal being met by its deadline.

## License

_Not specified._