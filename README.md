# Invoice Ninja Quarterly VAT Report CLI

This CLI application helps you generate a quarterly VAT tax report using data from your self-hosted Invoice Ninja v5 API. The report includes total invoice amounts, total expense amounts, and VAT calculations, and it saves the report as a markdown file.

## Example output

| Description                    | Amount    |
|:-------------------------------|:----------|
| Quarter                        | 2024-Q1   |
| Total amount billed            | €21120.55 |
| Exact amount billed ex BTW     | €17455.00 |
| Total BTW amount over invoices | €3665.55  |
| Total expenses                 | €420.15   |
| BTW paid over these expenses   | €46.24    |
| Total BTW difference           | €3619.31  |

## Installation

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # On Windows use `venv\Scripts\activate`
```

Install the required libraries:

```bash
pip install -r requirements.txt
```

Create a .env file in the root directory of your project with the following content:

```bash
cp .env.example .env
```

```env
API_KEY=your_api_key_here
API_URL=https://your-invoiceninja-url/api/v1
```

## Usage

Run the CLI with the desired options:

```bash
python app.py --year 2023 --quarter 2 --limit 100 --output report-2023-Q2.md
```

## Options

    --year: Year for the report (default: current year).
    --quarter: Quarter for the report (1-4, default: 1).
    --limit: Limit per request (default: 100).
    --output: Output file for the report (default: report-{year}-Q{quarter}.md).
