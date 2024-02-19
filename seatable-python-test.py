#!/usr/bin/env python
#
# This script prints the python version and all modules installed in the python runner container.
# This script also writes a row in the "Name" column of the current table, reads it and writes it again.

from seatable_api import Base, context
from seatable_api.constants import ColumnTypes

import sys
import subprocess


def main():
    server_url = context.server_url or "https://<your-seatable-server-url>"
    api_token = context.api_token or "<your-base-api-token>"

    base = Base(api_token, server_url)
    base.auth()

    print("Runner Container Python Version:):", sys.version)
    print("Installed packages:")
    pip_list = subprocess.check_output(["pip", "list"]).decode("utf-8")
    print(pip_list)

    print("Context ready, read/write test starting...")

    inital_row_data = {
        "Name": "This row is written by the python script, read and written again."
    }

    base.append_row(context.current_table, inital_row_data)

    row = base.list_rows(context.current_table, desc=True, order_by="Name", limit=100)

    newest_entry = max(row, key=lambda x: x["_ctime"])
    newest_name = newest_entry["Name"]

    row_data = {"Name": newest_name}

    base.append_row(context.current_table, row_data)


if __name__ == "__main__":
    main()
