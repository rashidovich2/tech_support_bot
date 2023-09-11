from pyairtable import Table
from pyairtable.formulas import match

from config import AIRTABLE_API_KEY, BASE_ID, TABLE_NAME

airtable_config = {'api_key': AIRTABLE_API_KEY,
                   'base_id': BASE_ID,
                   'table_name': TABLE_NAME}

phone_not_found_err = NameError('AirTable: phone number not found')


def find_name_by_phone(phone: str) -> str:
    table = Table(**airtable_config)
    phone_column_name = 'Phone'
    formula = match({phone_column_name: phone})
    record = table.first(formula=formula)
    if record is None:
        raise phone_not_found_err
    name_column_name = 'Name'
    try:
        name = record['fields'][name_column_name]
    except KeyError:
        name = ''
    return name
