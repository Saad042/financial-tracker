from datetime import date

from django.core.management.base import BaseCommand

from investments.crypto_prices import fetch_crypto_prices


class Command(BaseCommand):
    help = "Fetch crypto prices from CoinGecko for instruments with api_id set"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ticker",
            help="Only fetch for this instrument ticker (e.g., BTC)",
        )
        parser.add_argument(
            "--start-date",
            help="Start date in YYYY-MM-DD format (overrides auto-detection)",
        )
        parser.add_argument(
            "--end-date",
            help="End date in YYYY-MM-DD format (default: today)",
        )
        parser.add_argument(
            "--no-exchange-rate",
            action="store_true",
            help="Skip fetching USD/PKR exchange rate",
        )

    def handle(self, *args, **options):
        start_date = None
        end_date = None
        if options["start_date"]:
            start_date = date.fromisoformat(options["start_date"])
        if options["end_date"]:
            end_date = date.fromisoformat(options["end_date"])

        fetch_crypto_prices(
            fetch_exchange_rate=not options["no_exchange_rate"],
            stdout=self.stdout,
            ticker=options["ticker"],
            start_date=start_date,
            end_date=end_date,
        )
