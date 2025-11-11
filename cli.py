import logging
from src.logger import setup_logger
import getpass
import os

if __name__ == '__main__':
    setup_logger()
    database_url = getpass.getpass('Enter your database URI: ')
    if not database_url:
        database_url = "postgres://@localhost:5432/sd"

    os.environ['DATABASE_URL'] = database_url
    from src.cmd import BankCLI
    BankCLI().cmdloop()
