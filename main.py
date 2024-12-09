import json
import requests
import sys
import threading
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Enhanced UI and styling libraries
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live

class CurrencyConverter:
    # Comprehensive dictionary of world currencies
    WORLD_CURRENCIES = {
        'USD': {'name': 'United States Dollar', 'symbol': '$', 'rate': 1.0},
        'EUR': {'name': 'Euro', 'symbol': '€', 'rate': 0.93},
        'GBP': {'name': 'British Pound Sterling', 'symbol': '£', 'rate': 0.79},
        'JPY': {'name': 'Japanese Yen', 'symbol': '¥', 'rate': 147.50},
        'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$', 'rate': 1.35},
        'AUD': {'name': 'Australian Dollar', 'symbol': 'A$', 'rate': 1.52},
        'CHF': {'name': 'Swiss Franc', 'symbol': 'Fr.', 'rate': 0.91},
        'CNY': {'name': 'Chinese Yuan', 'symbol': '¥', 'rate': 7.15},
        'INR': {'name': 'Indian Rupee', 'symbol': '₹', 'rate': 83.20},
        'BRL': {'name': 'Brazilian Real', 'symbol': 'R$', 'rate': 4.95},
        'RUB': {'name': 'Russian Ruble', 'symbol': '₽', 'rate': 91.50},
        'KRW': {'name': 'South Korean Won', 'symbol': '₩', 'rate': 1300.50},
        'SGD': {'name': 'Singapore Dollar', 'symbol': 'S$', 'rate': 1.35},
        'MXN': {'name': 'Mexican Peso', 'symbol': '$', 'rate': 17.50},
        'SAR': {'name': 'Saudi Riyal', 'symbol': '﷼', 'rate': 3.75},
        'AED': {'name': 'UAE Dirham', 'symbol': 'د.إ', 'rate': 3.67},
        'TRY': {'name': 'Turkish Lira', 'symbol': '₺', 'rate': 30.50},
        'ZAR': {'name': 'South African Rand', 'symbol': 'R', 'rate': 18.50}
    }

    def __init__(self):
        self.console = Console()
        self.currencies = {}
        self.conversion_history = []
        self.rates_last_updated = None
        self.update_lock = threading.Lock()
        self.stop_update_thread = threading.Event()
        
        # Preload world currencies
        self._load_default_currencies()
        
        # Start live rate update thread
        self.rate_update_thread = threading.Thread(target=self._live_rate_updater, daemon=True)
        self.rate_update_thread.start()

    def _load_default_currencies(self):
        """Load default world currencies."""
        for code, details in self.WORLD_CURRENCIES.items():
            self.add_currency(
                code, 
                details['rate'], 
                details['symbol'], 
                details['name']
            )

    def _live_rate_updater(self):
        """Continuously update exchange rates in the background."""
        while not self.stop_update_thread.is_set():
            try:
                # Using a free exchange rate API
                response = requests.get('https://open.exchangerate-api.com/v6/latest')
                if response.status_code == 200:
                    rates = response.json().get('rates', {})
                    
                    # Thread-safe update of rates
                    with self.update_lock:
                        for code, rate in rates.items():
                            if code in self.currencies:
                                self.currencies[code].rate = rate
                        
                        self.rates_last_updated = datetime.now()
                
                # Wait for 15 minutes before next update
                time.sleep(900)  # 15 * 60 seconds
            
            except Exception as e:
                # Log error (or you could add more sophisticated error handling)
                print(f"Rate update error: {e}")
                # Wait 5 minutes before retrying if update fails
                time.sleep(300)

    def add_currency(self, code, rate, symbol='', full_name=''):
        """Add or update a currency."""
        class Currency:
            def __init__(self, code, rate, symbol='', full_name=''):
                self.code = code
                self.rate = rate
                self.symbol = symbol
                self.full_name = full_name
                self.amount = 0.0
        
        self.currencies[code] = Currency(code, rate, symbol, full_name)

    def convert(self, from_currency, to_currency, amount):
        """Convert between currencies."""
        try:
            # Ensure currencies exist
            if from_currency not in self.currencies or to_currency not in self.currencies:
                raise ValueError("One or both currencies not found")
            
            # Perform conversion with thread-safe rate access
            with self.update_lock:
                converted = (amount / self.currencies[from_currency].rate) * self.currencies[to_currency].rate
            
            # Record conversion history
            self.conversion_history.append({
                'from': from_currency,
                'to': to_currency,
                'amount': amount,
                'converted': converted,
                'date': datetime.now()
            })
            
            return converted
        
        except Exception as e:
            self.console.print(f"[red]Conversion Error: {e}[/red]")
            return None

    def display_currencies(self):
        """Display all available currencies with live updates."""
        def generate_currency_table():
            table = Table(title="Available Currencies")
            table.add_column("Code", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Symbol", style="green")
            table.add_column("Current Rate", style="yellow")
            table.add_column("Last Updated", style="dim")
            
            with self.update_lock:
                for code, currency in self.currencies.items():
                    table.add_row(
                        code, 
                        currency.full_name, 
                        currency.symbol, 
                        f"{currency.rate:.4f}",
                        self.rates_last_updated.strftime("%Y-%m-%d %H:%M:%S") if self.rates_last_updated else "Not updated"
                    )
            
            return table

        # Use Live display for real-time updates
        with Live(generate_currency_table(), console=self.console, refresh_per_second=0.5) as live:
            while True:
                time.sleep(5)  # Update every 5 seconds
                live.update(generate_currency_table())

                # Add a way to exit (optional)
                if not live.is_alive:
                    break

    def interactive_menu(self):
        """Main interactive menu."""
        while True:
            self.console.print(Panel(
                Text("💱 Live Currency Converter 💱", style="bold blue"),
                border_style="blue"
            ))
            
            options = [
                "Convert Currency",
                "View Live Currencies",
                "View Conversion History",
                "Exit"
            ]
            
            for i, option in enumerate(options, 1):
                self.console.print(f"[bold blue]{i}. {option}[/bold blue]")
            
            try:
                choice = input("Choose an option (1-4): ")
                choice = int(choice)
                
                if choice == 1:
                    self._convert_interactive()
                elif choice == 2:
                    self.display_currencies()
                elif choice == 3:
                    self._show_history()
                elif choice == 4:
                    # Stop the rate update thread before exiting
                    self.stop_update_thread.set()
                    break
                else:
                    self.console.print("[red]Invalid option. Try again.[/red]")
            
            except ValueError:
                self.console.print("[red]Please enter a valid number.[/red]")
            
            input("\nPress Enter to continue...")

    def _convert_interactive(self):
        """Interactive currency conversion."""
        # Briefly show available currencies
        self.console.print("\n[yellow]Available Currencies:[/yellow]")
        for code in self.currencies.keys():
            self.console.print(code, end=" ")
        print("\n")
        
        from_currency = input("Enter source currency code: ").upper()
        to_currency = input("Enter target currency code: ").upper()
        
        try:
            amount = float(input("Enter amount to convert: "))
            
            result = self.convert(from_currency, to_currency, amount)
            
            if result is not None:
                source_curr = self.currencies[from_currency]
                target_curr = self.currencies[to_currency]
                
                self.console.print(Panel(
                    f"[bold green]{source_curr.symbol}{amount:,.2f} {from_currency} = "
                    f"{target_curr.symbol}{result:,.2f} {to_currency}[/bold green]",
                    title="Conversion Result",
                    border_style="green"
                ))
        except ValueError as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def _show_history(self):
        """Display conversion history."""
        if not self.conversion_history:
            self.console.print("[yellow]No conversion history available.[/yellow]")
            return
        
        table = Table(title="Conversion History")
        table.add_column("From", style="cyan")
        table.add_column("To", style="magenta")
        table.add_column("Amount", style="green")
        table.add_column("Converted", style="yellow")
        table.add_column("Date", style="dim")
        
        for entry in reversed(self.conversion_history[-10:]):  # Last 10 entries
            table.add_row(
                entry['from'], 
                entry['to'], 
                f"{entry['amount']:,.2f}", 
                f"{entry['converted']:,.2f}", 
                entry['date'].strftime("%Y-%m-%d %H:%M")
            )
        
        self.console.print(table)

def main():
    console = Console()
    console.print("[bold blue]💱 Welcome to Live Currency Converter 💱[/bold blue]")
    
    converter = CurrencyConverter()
    
    try:
        converter.interactive_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled.[/red]")
    finally:
        # Ensure the update thread is stopped
        converter.stop_update_thread.set()
        console.print("[green]Thank you for using Currency Converter![/green]")

if __name__ == "__main__":
    main()
