# Set up LUSID
import os
import pandas as pd
import json
import uuid
import pytz
from IPython.core.display import HTML
from datetime import timedelta
import datetime
import pprint

import logging
logging.basicConfig(level=logging.INFO)

# LUSID
import lusid as lu
import lusid.api as la
import lusid.models as lm

# LUSID Drive
import lusid_drive as ld

from lusidjam import RefreshingToken
from lusidtools.pandas_utils.lusid_pandas import lusid_response_to_data_frame
from lusidtools.jupyter_tools import StopExecution
from lusidtools.lpt.lpt import to_date

# Set pandas display options
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.options.display.float_format = "{:,.2f}".format

#Setup pprint
pp = pprint.PrettyPrinter(indent=4)

# Authenticate to SDK
# Run the Notebook in Jupyterhub for your LUSID domain and authenticate automatically
secrets_path = os.getenv("FBN_SECRETS_PATH")

# Run the Notebook locally using a secrets file (see https://support.lusid.com/knowledgebase/article/KA-01663)
if secrets_path is None:
    secrets_path = os.path.join(os.path.dirname(os.getcwd()), "secrets.json")

lusid_api_factory = lu.utilities.ApiClientFactory(
    token=RefreshingToken(),
    api_secrets_filename=secrets_path,
    app_name="VSCode"
)

drive_api_factory = ld.utilities.ApiClientFactory(
    token=RefreshingToken(),
    api_secrets_filename=secrets_path,
    app_name="VSCode"
)

print('LUSID and Drive Environments Initialised')

# Definitions
scope = "api_challenges-4"
portfolio_code = "EQUITY_UK"

holdings_fields = [
    "instrument_uid",
    "holding_type",
    "units",
    "cost_portfolio_ccy",
    "holding_type_name",
]

holdings = {}

# Define API endpoints.
portfolio_api = lusid_api_factory.build(la.TransactionPortfoliosApi)
files_api = drive_api_factory.build(ld.api.FilesApi)

def date_string(date):
    return_string = f'_{date.day}_{date.month}_{date.year}'
    print(return_string)
    return return_string

# Get holdings from Lusid API.
try:
    return_holdings = portfolio_api.get_holdings(
        scope = scope,
        code = portfolio_code,
    )

    for return_holding in return_holdings.values:

        holding = {}
        
        holding["instrument_uid"] = return_holding.instrument_uid,
        holding["holding_type"] = return_holding.holding_type,
        holding["units"] = return_holding.units,
        holding["cost"] = return_holding.cost_portfolio_ccy.amount,
        holding["ccy"] = return_holding.cost_portfolio_ccy.currency,
        holding["holding_type_name"] = return_holding.holding_type_name,

        shk = max(return_holding.sub_holding_keys.keys())
        holding[shk] = return_holding.sub_holding_keys[shk].value.label_value
    
        holdings[return_holding.holding_id] = holding

except Exception as e:
    print(e)

df = pd.DataFrame()

for key, holding_dict in holdings.items():
    df = pd.concat([df, pd.DataFrame.from_dict(holding_dict)], ignore_index=True)

body_data = df.to_csv(
    header = True,
    index = False,
    lineterminator = '\n',
)

try:
    create_file_result = files_api.create_file(
        x_lusid_drive_filename = 'holdings' + date_string(datetime.date.today()) + '.csv',
        x_lusid_drive_path = f'API_Challenges/',
        content_length = len(body_data),
        body = body_data,
    )

    print(create_file_result)

except ld.ApiException as e:
    print(e)