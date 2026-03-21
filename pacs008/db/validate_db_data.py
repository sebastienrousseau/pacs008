# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Any

# Configure the logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)


def validate_db_data(data: list[dict[str, Any]]) -> bool:
    """
    Validate the data from a database.

    Args:
        data (list of dict): The data to validate.

    Returns:
        bool: True if the data is valid, False otherwise.
    """
    # Core required fields that must be present and non-null
    required_columns = [
        "msg_id",
        "creation_date_time",
        "nb_of_txs",
        "settlement_method",
        "end_to_end_id",
        "interbank_settlement_amount",
        "interbank_settlement_currency",
        "debtor_name",
        "debtor_agent_bic",
        "creditor_agent_bic",
        "creditor_name",
    ]

    for row in data:
        # Check only required columns
        for column in required_columns:
            if column not in row or row[column] is None or row[column] == "":
                logger.error(
                    "Error: Missing value for required column '%s' in row: %s",
                    column,
                    row,
                )
                return False
    return True
