from ctypes import ArgumentError
import os
from datetime import date, datetime
from typing import Optional

import click
import requests
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("API_KEY", None)
API_URL = os.getenv("API_URL", None)
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


def create_reports_directory(directory_name: str = "reports"):
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)


def generate_output_filename(year: int, quarter: int, directory_name: str = "reports", file_format: str = ".md"):
    output = f"report-{year}-Q{quarter}{file_format}"
    return os.path.join(directory_name, output)


def validate_arguments(year: int, quarter: int, limit: int, output: str):
    if not (year or quarter or limit or output):
        click.echo(generate_report.get_help(click.Context(generate_report)))
        return False
    if quarter < 1 or quarter > 4:
        click.echo(message="Error: Quarter must be between 1 and 4.")
        return False
    return True


def setup_headers(api_key: str):
    return {"X-Api-Token": api_key}


def generate_filter(**kwargs):
    return "?" + "&".join(f"{k}={v}" for k, v in kwargs.items())


def make_api_request(url: str, headers: dict, params: dict = None):
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response


def process_api_invoice_response(response, report: dict, quarter_dates: dict):
    invoices = response.json().get("data", [])

    for invoice in invoices:
        invoice_date = datetime.strptime(invoice["date"], "%Y-%m-%d")
        if not quarter_dates["start"] <= invoice_date.date() <= quarter_dates["end"]:
            continue

        btw = invoice["total_taxes"]
        ex_btw = invoice["amount"] - btw

        report["total_billed"] += invoice["amount"]
        report["total_billed_ex_btw"] += ex_btw
        report["total_btw_invoices"] += btw

    return report


def process_api_expense_response(response, report: dict, quarter_dates: dict):
    expenses = response.json().get("data", [])

    for expense in expenses:
        expense_date = datetime.strptime(expense["date"], "%Y-%m-%d")
        if not quarter_dates["start"] <= expense_date.date() <= quarter_dates["end"]:
            continue

        expense_btw = 0
        if expense["tax_rate1"] == 21:
            expense_btw = expense["amount"] * 0.21
            report["total_btw_expenses"] += expense_btw

        report["total_expenses"] += expense["amount"]

    return report


def validate_environment_variables(api_key: Optional[str], api_url: Optional[str]):
    if not api_key:
        click.echo(message="Error: API_KEY is not set. Please set it in your environment variables.")
        raise ArgumentError("API_KEY is not set.")
    if not api_url:
        click.echo(message="Error: API_URL is not set. Please set it in your environment variables.")
        raise ArgumentError("API_URL is not set.")
    return


def create_table_report(report: dict):
    # Calculate total difference
    report["total_difference"] = report["total_btw_invoices"] - report["total_btw_expenses"]

    # build report
    report_data = [
        ["Quarter", f"{report['year']}-Q{report['quarter']}"],
        ["Total amount billed", f"€{report['total_billed']:.2f}"],
        ["Exact amount billed ex BTW", f"€{report['total_billed_ex_btw']:.2f}"],
        ["Total BTW amount over invoices", f"€{report['total_btw_invoices']:.2f}"],
        ["Total expenses", f"€{report['total_expenses']:.2f}"],
        ["BTW paid over these expenses", f"€{report['total_btw_expenses']:.2f}"],
        ["Total BTW difference", f"€{report['total_difference']:.2f}"],
    ]

    return tabulate(report_data, headers=["Description", "Amount"], tablefmt="pipe")


def write_report_to_file(report: str, output: str):
    with open(output, "w") as file:
        file.write(report)
    return


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--year", required=True, default=date.today().year, help="Year for the report")
@click.option("--quarter", required=True, type=int, help="Quarter for the report (1-4)")
@click.option("--limit", default=100, help="Limit per request")
@click.option("--output", default=None, help="Output file for the report")
def generate_report(year, quarter, limit, output):
    validate_environment_variables(API_KEY, API_URL)
    create_reports_directory()

    if output is None:
        output = generate_output_filename(year, quarter)

    if not validate_arguments(int(year), int(quarter), int(limit), output):
        click.Abort()

    current_date = date(int(year), 1, 1)
    quarter_dates = get_quarter_dates(current_date, int(quarter))

    # setup start values
    report = {
        "year": year,
        "quarter": quarter,
        "total_billed": 0,
        "total_billed_ex_btw": 0,
        "total_btw_invoices": 0,
        "total_expenses": 0,
        "total_btw_expenses": 0,
        "total_difference": 0,
    }

    headers = setup_headers(API_KEY)

    invoice_filter = generate_filter(
        include="client",
        without_deleted_clients="true",
        sort="id|desc",
        per_page=limit,
        page=1,
        filter="",
        client_status="paid,overdue",
        status="active",
    )

    expense_filter = generate_filter(
        include="client,vendor,category",
        without_deleted_clients="true",
        without_deleted_vendors="true",
        sort="date|desc",
        per_page=limit,
        page=1,
        filter="",
        client_status="",
        status="active",
    )

    # Get invoices
    inv_response = make_api_request(f"{INVOICES_URL}{invoice_filter}", headers)
    report = process_api_invoice_response(inv_response, report, quarter_dates)

    # Get expenses
    exp_response = make_api_request(f"{EXPENSES_URL}{expense_filter}", headers)
    report = process_api_expense_response(exp_response, report, quarter_dates)

    pretty_report = create_table_report(report=report)

    write_report_to_file(report=pretty_report, output=output)
    click.echo(f"Report has been written to {output}")


if __name__ == "__main__":
    generate_report()
