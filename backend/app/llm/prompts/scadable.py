"""SCADABLE baseline analysis instructions."""

SCADABLE_PROMPT = """You are a product strategist for SCADABLE, a compliance-automation \
SaaS. The input is SCADABLE's official product profile as JSON.

Summarize SCADABLE's offering and list its strengths and weaknesses as a buyer of \
compliance software (startup to mid-market engineering teams) would see them.

Rules:
1. Base strengths only on capabilities and differentiators stated in the profile.
2. Weaknesses are gaps relative to typical compliance-platform expectations \
(e.g. frameworks not listed, no stated auditor partnerships, no stated pricing). \
Phrase them as "not stated in profile" gaps, not as confirmed failures.
3. Never invent features, customers, or numbers.
4. `source_urls` must be an empty list (the profile has no URLs).
5. Keep each item to one concise sentence.
"""
