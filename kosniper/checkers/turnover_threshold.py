import re
from typing import Any, Dict, List, Optional, Tuple

from kosniper.contracts import CheckerResult, EvidenceSpan, TrafficLight


class TurnoverThresholdChecker:
    """Deterministic checker for turnover threshold requirements (Mindestumsatz/Jahresumsatz).

    Compares extracted thresholds against company profile turnover.
    Rule: RED only when threshold is unambiguous AND company is clearly below.
    """

    name = "TurnoverThresholdChecker"

    # Turnover keywords (case-insensitive)
    TURNOVER_KEYWORDS = [
        "mindestumsatz",
        "mindestjahresumsatz",
        "jahresumsatz",
        "gesamtumsatz",
        "umsatz",
    ]

    # Currency markers (case-insensitive)
    CURRENCY_MARKERS = ["€", "eur", "euro"]

    # Ambiguity triggers (case-insensitive)
    AMBIGUITY_PATTERNS = [
        r"zwischen\s+[\d.,]+\s*(und|bis)",
        r"von\s+[\d.,]+\s*bis",
        r"durchschnitt",
        r"letzten\s+\d+\s+gesch[äa]ftsjahre",
        r"drei\s+gesch[äa]ftsjahre",
        r"im\s+mittel",
        r"je\s+los",
        r"pro\s+los",
        r"f[üu]r\s+los",
        r"in\s+summe",
        r"relevanten?\s+gesch[äa]ftsbereich",
    ]

    def _normalize_text(self, text: str) -> str:
        """Normalize text: handle hyphenation at line breaks, collapse whitespace."""
        if not text:
            return ""
        # Handle hyphenation at line breaks
        normalized = re.sub(r"-\s*\n\s*", "", text)
        # Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _parse_german_number(self, num_str: str, multiplier: Optional[str]) -> Optional[float]:
        """Parse German-formatted number with optional multiplier."""
        # Clean the number string
        num_str = num_str.strip()
        if not num_str:
            return None

        # Remove thousands separators (. followed by exactly 3 digits)
        # Work from right to left to handle multiple separators
        parsed = re.sub(r"\.(?=\d{3}(?:\D|$))", "", num_str)

        # Convert decimal separator (, -> .)
        parsed = parsed.replace(",", ".")

        try:
            value = float(parsed)
        except ValueError:
            return None

        # Apply multiplier
        if multiplier:
            mult_lower = multiplier.lower().strip()
            if "mio" in mult_lower or "million" in mult_lower:
                value *= 1_000_000
            elif "tsd" in mult_lower or mult_lower in ("t", "t€", "teur"):
                value *= 1_000

        return value

    def _find_turnover_requirements(
        self, text: str
    ) -> List[Tuple[float, str, int, int]]:
        """Find turnover requirements in text.

        Returns list of (value_eur, snippet, start, end) tuples.
        De-duplicates overlapping keyword matches.
        """
        text_lower = text.lower()
        results = []
        covered_positions = set()  # Track positions already matched

        # Find all turnover keywords (longer/more specific first to avoid duplicates)
        sorted_keywords = sorted(self.TURNOVER_KEYWORDS, key=len, reverse=True)

        for keyword in sorted_keywords:
            for match in re.finditer(re.escape(keyword), text_lower):
                kw_start = match.start()
                kw_end = match.end()

                # Skip if this position overlaps with already-matched keyword
                if any(kw_start <= pos < kw_end or pos <= kw_start < pos + 20
                       for pos in covered_positions):
                    continue

                # Search window around keyword (120 chars each direction)
                window_start = max(0, kw_start - 120)
                window_end = min(len(text), kw_end + 120)
                window = text[window_start:window_end]
                window_lower = window.lower()

                # Check for currency in window
                has_currency = any(
                    curr in window_lower for curr in self.CURRENCY_MARKERS
                )

                if not has_currency:
                    continue

                # Look for number pattern with optional multiplier
                # Pattern: digits with . or , separators, optional Mio./Tsd. suffix
                number_pattern = r"([\d.,]+)\s*(mio\.?|million(?:en)?|tsd\.?|t\s*€|teur)?"

                for num_match in re.finditer(number_pattern, window_lower):
                    num_str = num_match.group(1)
                    multiplier = num_match.group(2)

                    # Validate: number must have at least 2 digits (avoid matching "3" in "3 Jahre")
                    if not re.search(r"\d{2,}", num_str.replace(".", "").replace(",", "")):
                        continue

                    # Check currency is near this number (within 15 chars)
                    num_end_in_window = num_match.end()
                    nearby_text = window_lower[
                        max(0, num_match.start() - 15) : num_end_in_window + 15
                    ]
                    if not any(curr in nearby_text for curr in self.CURRENCY_MARKERS):
                        continue

                    value = self._parse_german_number(num_str, multiplier)
                    if value is not None and value > 0:
                        # Extract snippet
                        snippet_start = max(0, kw_start - 40)
                        snippet_end = min(len(text), kw_end + 80)
                        snippet = text[snippet_start:snippet_end].strip()

                        results.append((value, snippet, kw_start, kw_end))
                        covered_positions.add(kw_start)
                        break  # One value per keyword occurrence

        # De-duplicate by value (same threshold mentioned multiple ways)
        unique_values = {}
        for value, snippet, start, end in results:
            if value not in unique_values:
                unique_values[value] = (value, snippet, start, end)

        return list(unique_values.values())

    def _has_ambiguity(self, text: str) -> bool:
        """Check if text contains ambiguity triggers."""
        text_lower = text.lower()
        for pattern in self.AMBIGUITY_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def _has_multiple_scope_qualifiers(self, text: str) -> bool:
        """Check for multiple distinct turnover scopes (gesamtumsatz vs relevanter bereich)."""
        text_lower = text.lower()
        has_gesamt = "gesamtumsatz" in text_lower
        has_bereich = "relevanten" in text_lower and "bereich" in text_lower
        return has_gesamt and has_bereich

    def run(
        self,
        text: Optional[str],
        doc_id: str,
        page_number: int,
        company_profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[CheckerResult]:
        """Run the turnover threshold checker.

        Returns CheckerResult or None (for zero findings / neutral).
        """
        # Normalize text
        normalized = self._normalize_text(text) if text else ""

        # Stop condition: empty text -> ABSTAIN
        if not normalized:
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.ABSTAIN,
                reason="no_text",
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet="(no text)",
                    )
                ],
            )

        # Check for any turnover keyword first
        text_lower = normalized.lower()
        has_turnover_keyword = any(kw in text_lower for kw in self.TURNOVER_KEYWORDS)

        if not has_turnover_keyword:
            # No turnover requirement detected -> zero findings (neutral)
            return None

        # Check for currency marker near turnover keywords
        has_currency_near_keyword = False
        for keyword in self.TURNOVER_KEYWORDS:
            for match in re.finditer(re.escape(keyword), text_lower):
                window_start = max(0, match.start() - 120)
                window_end = min(len(normalized), match.end() + 120)
                window = text_lower[window_start:window_end]
                if any(curr in window for curr in self.CURRENCY_MARKERS):
                    has_currency_near_keyword = True
                    break
            if has_currency_near_keyword:
                break

        if not has_currency_near_keyword:
            # Turnover keyword but no currency -> YELLOW missing_currency
            # Find snippet around first turnover keyword
            for keyword in self.TURNOVER_KEYWORDS:
                match = re.search(re.escape(keyword), text_lower)
                if match:
                    snippet_start = max(0, match.start() - 40)
                    snippet_end = min(len(normalized), match.end() + 80)
                    snippet = normalized[snippet_start:snippet_end].strip()
                    break
            else:
                snippet = normalized[:120]

            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.YELLOW,
                reason="missing_currency",
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=snippet,
                    )
                ],
            )

        # Check for ambiguity patterns
        if self._has_ambiguity(normalized):
            # Find snippet around first turnover keyword
            for keyword in self.TURNOVER_KEYWORDS:
                match = re.search(re.escape(keyword), text_lower)
                if match:
                    snippet_start = max(0, match.start() - 40)
                    snippet_end = min(len(normalized), match.end() + 80)
                    snippet = normalized[snippet_start:snippet_end].strip()
                    break
            else:
                snippet = normalized[:120]

            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.YELLOW,
                reason="ambiguous_requirement",
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=snippet,
                    )
                ],
            )

        # Check for multiple scope qualifiers
        if self._has_multiple_scope_qualifiers(normalized):
            snippet = normalized[:120]
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.YELLOW,
                reason="ambiguous_requirement",
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=snippet,
                    )
                ],
            )

        # Extract turnover requirements
        requirements = self._find_turnover_requirements(normalized)

        if len(requirements) == 0:
            # Keyword + currency but couldn't parse number -> zero findings
            return None

        if len(requirements) > 1:
            # Multiple thresholds -> YELLOW ambiguous
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.YELLOW,
                reason="ambiguous_threshold_count",
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=requirements[0][1],
                    )
                ],
            )

        # Single unambiguous threshold
        threshold_eur, snippet, _, _ = requirements[0]

        # Check company profile
        if company_profile is None or "annual_turnover_eur" not in company_profile:
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.YELLOW,
                reason="missing_company_turnover",
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=snippet,
                    )
                ],
            )

        company_turnover = company_profile.get("annual_turnover_eur")
        if company_turnover is None:
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.YELLOW,
                reason="missing_company_turnover",
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=snippet,
                    )
                ],
            )

        # Compare
        if company_turnover < threshold_eur:
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.RED,
                reason="below_threshold",
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=snippet,
                    )
                ],
            )

        # Company meets or exceeds threshold -> zero findings (neutral)
        return None
