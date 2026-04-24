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

"""Keyword Planner tools — volume, competition, and bid ideas.

This is the "find keyword ideas for my niche" surface. It wraps
KeywordPlanIdeaService so the LLM can ask things like "give me keyword ideas
for 'project management software' in the US with monthly search volume and
competitive bid ranges."
"""

from typing import Any

from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp
from ads_mcp.tools import _common


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def generate_keyword_ideas(
    customer_id: str,
    keywords: list[str] | None = None,
    page_url: str | None = None,
    geo_target_constant_ids: list[str] | None = None,
    language_id: str = "1000",
    include_adult_keywords: bool = False,
    network: str = "GOOGLE_SEARCH_AND_PARTNERS",
    page_size: int = 50,
) -> list[dict[str, Any]]:
    """Generates keyword ideas with monthly searches, competition, and bid ranges.

    Use this whenever the user asks for keyword research, competitive analysis,
    or "what should I bid on?". Returns one row per idea with:
      - text: the keyword
      - avg_monthly_searches: average monthly search volume
      - competition: 'UNSPECIFIED' | 'UNKNOWN' | 'LOW' | 'MEDIUM' | 'HIGH'
      - competition_index: 0..100
      - low_top_of_page_bid_micros / high_top_of_page_bid_micros: CPC bid range
      - monthly_search_volumes: list of the last ~12 months

    Seed at least one of `keywords` or `page_url` (you can pass both to combine).

    Args:
        customer_id: 10-digit customer id (the Ads account to bill for the lookup).
        keywords: Seed phrases (e.g. ["crm software", "sales pipeline"]). Up to 20.
        page_url: Seed URL (Google scrapes it for topical keywords).
        geo_target_constant_ids: Numeric geo target IDs from
            search_geo_target_constants. If empty, worldwide.
        language_id: Numeric language constant id (default 1000 = English,
            1019 = Hindi, 1003 = Spanish, 1002 = French).
        include_adult_keywords: Include sexually-explicit terms. Default False.
        network: 'GOOGLE_SEARCH' or 'GOOGLE_SEARCH_AND_PARTNERS'.
        page_size: Max ideas to return (API hard cap ~10000; this truncates).
    """
    if not keywords and not page_url:
        raise ValueError(
            "Pass at least one of `keywords` or `page_url` so Keyword Planner "
            "has something to seed on."
        )

    client = utils.get_googleads_client()
    service = client.get_service("KeywordPlanIdeaService")
    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = customer_id
    request.language = _common.language_constant_path(language_id)
    request.include_adult_keywords = include_adult_keywords
    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum[
        network
    ]
    if geo_target_constant_ids:
        request.geo_target_constants.extend(
            [
                _common.geo_target_constant_path(g)
                for g in geo_target_constant_ids
            ]
        )

    if keywords and page_url:
        request.keyword_and_url_seed.url = page_url
        request.keyword_and_url_seed.keywords.extend(keywords)
    elif keywords:
        request.keyword_seed.keywords.extend(keywords)
    elif page_url:
        request.url_seed.url = page_url

    with _common.google_ads_errors():
        response = service.generate_keyword_ideas(request=request)

    out: list[dict[str, Any]] = []
    for idea in response:
        metrics = idea.keyword_idea_metrics
        monthly_volumes = []
        for mv in metrics.monthly_search_volumes:
            monthly_volumes.append(
                {
                    "year": mv.year,
                    "month": mv.month.name if hasattr(mv.month, "name") else str(mv.month),
                    "monthly_searches": mv.monthly_searches,
                }
            )
        out.append(
            {
                "text": idea.text,
                "avg_monthly_searches": metrics.avg_monthly_searches,
                "competition": metrics.competition.name
                if hasattr(metrics.competition, "name")
                else str(metrics.competition),
                "competition_index": metrics.competition_index,
                "low_top_of_page_bid_micros": metrics.low_top_of_page_bid_micros,
                "high_top_of_page_bid_micros": metrics.high_top_of_page_bid_micros,
                "monthly_search_volumes": monthly_volumes,
            }
        )
        if len(out) >= page_size:
            break
    return out
