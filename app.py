import os
from datetime import date, datetime

import click
import requests
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
INVOICES_URL = f"{API_URL}/invoices"
EXPENSES_URL = f"{API_URL}/expenses"


def get_quarter_dates(current_date: datetime, quarter: int) -> dict:
    if quarter < 1 or quarter > 4:
        raise ValueError("Quarter must be between 1 and 4.")

    year = current_date.year
    quarter_dates = {
        1: {"start": date(year, 1, 1), "end": date(year, 3, 31)},
        2: {"start": date(year, 4, 1), "end": date(year, 6, 30)},
        3: {"start": date(year, 7, 1), "end": date(year, 9, 30)},
        4: {"start": date(year, 10, 1), "end": date(year, 12, 31)},
    }

    return quarter_dates[quarter]


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--year", default=date.today().year, help="Year for the report")
@click.option("--quarter", default=1, help="Quarter for the report (1-4)")
@click.option("--limit", default=100, help="Limit per request")
@click.option("--output", default=None, help="Output file for the report")
def generate_report(year, quarter, limit, output):
    # Ensure the reports directory exists
    if not os.path.exists("reports"):
        os.makedirs("reports")

    if output is None:
        output = f"report-{year}-Q{quarter}.md"

    # Modify the output path to include the reports directory
    output = os.path.join("reports", output)

    if not (year or quarter or limit or output):
        click.echo(generate_report.get_help(click.Context(generate_report)))
        return

    current_date = date(year, 1, 1)
    quarter_dates = get_quarter_dates(current_date, quarter)

    headers = {
        "X-Api-Token": API_KEY,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
    }

    invoice_filter = f"?include=client&without_deleted_clients=true&sort=id|desc&per_page={limit}&page=1&filter=&client_status=paid,overdue&status=active"
    response = requests.get(
        f"{INVOICES_URL}{invoice_filter}",
        headers=headers,
    )
    invoices = response.json().get("data", [])

    expense_filter = f"?include=client,vendor,category&without_deleted_clients=true&without_deleted_vendors=true&sort=date|desc&per_page={limit}&page=1&filter=&client_status=&status=active"
    response = requests.get(
        f"{EXPENSES_URL}{expense_filter}",
        headers=headers,
    )
    expenses = response.json().get("data", [])

    total_billed = 0
    total_billed_ex_btw = 0
    total_btw_invoices = 0
    total_expenses = 0
    total_btw_expenses = 0

    for invoice in invoices:
        invoice_date = datetime.strptime(invoice["date"], "%Y-%m-%d")
        if not quarter_dates["start"] <= invoice_date.date() <= quarter_dates["end"]:
            continue

        btw = invoice["total_taxes"]
        ex_btw = invoice["amount"] - btw

        total_billed += invoice["amount"]
        total_billed_ex_btw += ex_btw
        total_btw_invoices += btw

    for expense in expenses:
        expense_date = datetime.strptime(expense["date"], "%Y-%m-%d")
        if not quarter_dates["start"] <= expense_date.date() <= quarter_dates["end"]:
            continue

        expense_btw = 0
        if expense["tax_rate1"] == 21:
            expense_btw = expense["amount"] * 0.21
            total_btw_expenses += expense_btw

        total_expenses += expense["amount"]

    total_difference = total_btw_invoices - total_btw_expenses

    report_data = [
        ["Quarter", f"{year}-Q{quarter}"],
        ["Total amount billed", f"€{total_billed:.2f}"],
        ["Exact amount billed ex BTW", f"€{total_billed_ex_btw:.2f}"],
        ["Total BTW amount over invoices", f"€{total_btw_invoices:.2f}"],
        ["Total expenses", f"€{total_expenses:.2f}"],
        ["BTW paid over these expenses", f"€{total_btw_expenses:.2f}"],
        ["Total BTW difference", f"€{total_difference:.2f}"],
    ]

    with open(output, "w") as file:
        file.write(tabulate(report_data, headers=["Description", "Amount"], tablefmt="pipe"))

    click.echo(f"Report generated: {output}")


if __name__ == "__main__":
    generate_report()
