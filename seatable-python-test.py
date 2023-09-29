#!/usr/bin/env python
#
# This script prints the python version and all modules installed in the python runner container.
# This script also writes a row in the "Name" column of the current table, reads it and writes it again.

from seatable_api import Base, context
from seatable_api.constants import ColumnTypes

import sys

def main():
    server_url = context.server_url or 'https://<your-seatable-server-url>'
    api_token = context.api_token or '<your-base-api-token>'

    base = Base(api_token, server_url)
    base.auth()

    print("Python version:", sys.version)
    print("Modules:")
    for module in sys.modules.keys():
        if not module.startswith('_'):
            print(module)

    print("Context ready, read/write test starting...")

    inital_rows_data = [{
                'Name': 'This row is written by the python script, read and written again.'
            }]

    base.batch_append_rows(context.current_table, inital_rows_data)

    rows = base.list_rows(context.current_table, limit=1)

    # Filter out key-value pairs with '_' in the key
    filtered_rows = [{k: v for k, v in item.items() if not k.startswith('_')} for item in rows]

    print(filtered_rows)

    base.batch_append_rows(context.current_table, filtered_rows)

if __name__ == "__main__":
    main()
