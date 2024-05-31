# Set up
import os
import pandas as pd
import json
import uuid
import pytz
from datetime import timedelta
import datetime
import pprint

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# LUSID
import lusid as lu
import lusid.api as la
import lusid.models as lm
import lusid_drive as ld
from lusidjam import RefreshingToken

# Set pandas display options.
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.options.display.float_format = "{:,.2f}".format

# Function definitions.
def date_string(date):
    return_string = f'_{date.day}_{date.month}_{date.year}'
    return return_string

# Handle API creating accross all endpoints.
def create_fbn_endpoints(*args):
    factories = []

    for endpoint in args:
        factories.append(
            endpoint.utilities.ApiClientFactory(
                token=RefreshingToken(),
                api_secrets_filename=secrets_path,
                app_name="VSCode"
            )
        )

    return tuple(factories)

# Variable definitions.
pp = pprint.PrettyPrinter(indent=4)

scope = "api_challenges-4"
portfolio_code = "EQUITY_UK"
drive_path = "API_Challenges"
filename_prefix = 'holdings'

holdings = {}

# Attempt to determine the path of the secrets file.
secrets_path = os.getenv("FBN_SECRETS_PATH")
username = os.getenv("FBN_USERNAME")

logger.debug(f"username is {username}")

# Default to using env variables if no secrets file.
if secrets_path is None:
    logger.info("Using env variables for API Factory initialiastion.")
    lusid_api_factory, drive_api_factory = create_fbn_endpoints(lu, ld)

# Otherwise, use secerets file if it exists.
else:
    logger.info("Using secrets.json file for API Factory initialiastion.")
    lusid_api_factory, drive_api_factory = create_fbn_endpoints(lu, ld)

logger.info('LUSID and Drive Environments Initialised')

# Define API endpoints.
portfolio_api = lusid_api_factory.build(la.TransactionPortfoliosApi)
files_api = drive_api_factory.build(ld.api.FilesApi)

# Get holdings from Lusid API.
try:
    return_holdings = portfolio_api.get_holdings(
        scope = scope,
        code = portfolio_code,
    )

except Exception as e:
    logger.debug(e)
    logger.info("Holdings request failed.")

# Map each holding into it's own dictionary within the holding list.
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

# Dataframe to collect data into.
df = pd.DataFrame()

# Map holdings dict to dataframe.
for key, holding_dict in holdings.items():
    df = pd.concat([df, pd.DataFrame.from_dict(holding_dict)], ignore_index=True)

# Convert dataframe to CSV string.
body_data = df.to_csv(
    header = True,
    index = False,
    lineterminator = '\n',
)

# Upload to drive.
try:
    create_file_result = files_api.create_file(
        x_lusid_drive_filename = f'{filename_prefix}' + date_string(datetime.date.today()) + '.csv',
        x_lusid_drive_path = f'{drive_path}/',
        content_length = len(body_data),
        body = body_data,
    )

    logger.info(create_file_result)

except ld.ApiException as e:
    logger.debug(e)
    logger.info("Report creation failed.")