
import asyncio
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIAnalysisError(Exception):
    """Raised when AI interpretation fails or returns invalid data."""


SYSTEM_PROMPT = """
You are the AI interpretation assistant for LovetechCyber AI Forex Analyst.

Your responsibility is to interpret technical market analysis supplied
by the existing analysis engine.

You must:
1. Interpret market structure, BOS, CHoCH, FVG, liquidity sweeps,
   liquidity zones, order blocks and technical indicators.
2. Compare bullish and bearish evidence.
3. Produce bullish and bearish market scenarios.
4. Explain possible entry areas ONLY when supported by supplied data.
5. Identify invalidation conditions ONLY when supported by supplied data.
6. Identify conflicting signals and market risks.
7. Explain the reasoning behind your interpretation.
8. Distinguish confirmed engine findings from AI interpretation.
9. Never invent prices, candle data, indicators or market events.
10. Never claim that a trade is guaranteed.
11. Never execute trades or instruct an automated trading system
    to execute trades.
12. Recommend human analyst confirmation before any trading decision.

If evidence is insufficient, explicitly say so.

Return valid JSON only, using this structure:

{
  "market_bias": "bullish | bearish | neutral | uncertain",
  "confidence": "low | medium | high",
  "summary": "string",
  "bullish_scenario": {
    "conditions": [],
    "supporting_evidence": [],
    "invalidation": []
  },
  "bearish_scenario": {
    "conditions": [],
    "supporting_evidence": [],
    "invalidation": []
  },
  "key_levels_and_zones": [],
  "risk_factors": [],
  "conflicting_evidence": [],
  "analyst_recommendation": "string",
  "human_confirmation_required": true
}

Do not manufacture missing information.
"""


def _validate_response(data: Any) -> dict:
    if not isinstance(data, dict):
        raise AIAnalysisError("AI returned an invalid response.")

    required = [
        "market_bias",
        "confidence",
        "summary",
        "bullish_scenario",
        "bearish_scenario",
        "key_levels_and_zones",
        "risk_factors",
        "conflicting_evidence",
        "analyst_recommendation",
        "human_confirmation_required",
    ]

    missing = [field for field in required if field not in data]

    if missing:
        raise AIAnalysisError(
            f"AI response is missing fields: {', '.join(missing)}"
        )

    if data["market_bias"] not in {
        "bullish", "bearish", "neutral", "uncertain"
    }:
        raise AIAnalysisError("Invalid market bias.")

    if data["confidence"] not in {"low", "medium", "high"}:
        raise AIAnalysisError("Invalid confidence level.")

    if not isinstance(data["summary"], str):
        raise AIAnalysisError("Invalid AI summary.")

    if not isinstance(data["analyst_recommendation"], str):
        raise AIAnalysisError("Invalid analyst recommendation.")

    for scenario_name in ("bullish_scenario", "bearish_scenario"):
        scenario = data[scenario_name]

        if not isinstance(scenario, dict):
            raise AIAnalysisError(f"Invalid {scenario_name}.")

        for field in ("conditions", "supporting_evidence", "invalidation"):
            if not isinstance(scenario.get(field), list):
                raise AIAnalysisError(
                    f"Invalid {scenario_name}.{field}"
                )

    for field in (
        "key_levels_and_zones",
        "risk_factors",
        "conflicting_evidence",
    ):
        if not isinstance(data[field], list):
            raise AIAnalysisError(f"Invalid {field}.")

    # Human review is mandatory regardless of the model's output.
    data["human_confirmation_required"] = True

    return data


def _request_ai_interpretation(
    market_analysis: dict,
    multi_timeframe_analysis: dict | None = None,
) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise AIAnalysisError(
            "OPENAI_API_KEY is not configured."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    base_url = os.getenv(
        "OPENAI_BASE_URL",
        "https://api.openai.com/v1"
    ).rstrip("/")

    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "single_timeframe_analysis": market_analysis,
                        "multi_timeframe_analysis": (
                            multi_timeframe_analysis
                        ),
                    },
                    default=str,
                ),
            },
        ],
    }

    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AIAnalysisError(
            f"AI provider returned HTTP {exc.code}: {detail[:500]}"
        ) from exc

    except (URLError, TimeoutError) as exc:
        raise AIAnalysisError(
            f"Could not connect to AI provider: {exc}"
        ) from exc

    except (json.JSONDecodeError, OSError) as exc:
        raise AIAnalysisError(
            "Unable to process the AI provider response."
        ) from exc

    try:
        content = result["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise AIAnalysisError(
            "AI provider returned an unreadable response."
        ) from exc

    return _validate_response(parsed)


async def analyze_with_ai(
    market_analysis: dict,
    multi_timeframe_analysis: dict | None = None,
) -> dict:
    if not isinstance(market_analysis, dict) or not market_analysis:
        raise AIAnalysisError(
            "Valid single-timeframe analysis is required."
        )

    if (
        multi_timeframe_analysis is not None
        and not isinstance(multi_timeframe_analysis, dict)
    ):
        raise AIAnalysisError(
            "Multi-timeframe analysis must be an object."
        )

    result = await asyncio.to_thread(
        _request_ai_interpretation,
        market_analysis,
        multi_timeframe_analysis,
    )

    return {
        "success": True,
        "provider": "openai",
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "interpretation": result,
        "execution_enabled": False,
        "human_confirmation_required": True,
    }
