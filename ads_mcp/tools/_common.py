# Copyright 2026 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared helpers for mutate-style tools."""

from contextlib import contextmanager
from typing import Iterable

from fastmcp.exceptions import ToolError
from google.ads.googleads.errors import GoogleAdsException

import ads_mcp.utils as utils


def customer_path(customer_id: str) -> str:
    return f"customers/{customer_id}"


def campaign_path(customer_id: str, campaign_id: str | int) -> str:
    return f"customers/{customer_id}/campaigns/{campaign_id}"


def campaign_budget_path(customer_id: str, budget_id: str | int) -> str:
    return f"customers/{customer_id}/campaignBudgets/{budget_id}"


def ad_group_path(customer_id: str, ad_group_id: str | int) -> str:
    return f"customers/{customer_id}/adGroups/{ad_group_id}"


def ad_group_ad_path(
    customer_id: str, ad_group_id: str | int, ad_id: str | int
) -> str:
    return f"customers/{customer_id}/adGroupAds/{ad_group_id}~{ad_id}"


def ad_group_criterion_path(
    customer_id: str, ad_group_id: str | int, criterion_id: str | int
) -> str:
    return (
        f"customers/{customer_id}/adGroupCriteria/{ad_group_id}~{criterion_id}"
    )


def campaign_criterion_path(
    customer_id: str, campaign_id: str | int, criterion_id: str | int
) -> str:
    return (
        f"customers/{customer_id}/campaignCriteria/{campaign_id}~{criterion_id}"
    )


def conversion_action_path(
    customer_id: str, conversion_action_id: str | int
) -> str:
    return (
        f"customers/{customer_id}/conversionActions/{conversion_action_id}"
    )


def geo_target_constant_path(geo_target_id: str | int) -> str:
    return f"geoTargetConstants/{geo_target_id}"


def language_constant_path(language_id: str | int) -> str:
    return f"languageConstants/{language_id}"


def micros(amount: float | int) -> int:
    """Convert a money amount (e.g. 12.34 USD) to micros (12340000)."""
    return int(round(float(amount) * 1_000_000))


@contextmanager
def google_ads_errors():
    """Translate GoogleAdsException into ToolError with request_id and details."""
    try:
        yield
    except GoogleAdsException as ex:
        error_msgs = [
            f"{error.error_code}: {error.message}"
            for error in ex.failure.errors
        ]
        raise ToolError(
            f"Google Ads API request {ex.request_id} failed:\n"
            + "\n".join(error_msgs)
        ) from ex


def set_field_mask(operation, *paths: str) -> None:
    """Append paths to operation.update_mask.paths, deduplicated."""
    existing = set(operation.update_mask.paths)
    for p in paths:
        if p not in existing:
            operation.update_mask.paths.append(p)
            existing.add(p)


def gaql_search(customer_id: str, query: str) -> list[dict]:
    """Run a GAQL query and return rows formatted via utils.format_output_row."""
    ga_service = utils.get_googleads_service("GoogleAdsService")
    with google_ads_errors():
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        out: list[dict] = []
        for batch in stream:
            for row in batch.results:
                out.append(
                    utils.format_output_row(row, batch.field_mask.paths)
                )
        return out


def mutate_summary(response, op_kind: str) -> list[dict]:
    """Summarize a mutate response into a list of {resource_name} (or status)."""
    results = []
    for r in response.results:
        results.append({"resource_name": r.resource_name})
    return [{"operation": op_kind, "results": results}]


def comma_join(items: Iterable[str]) -> str:
    return ", ".join(f"'{i}'" for i in items)
