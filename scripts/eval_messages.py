"""Evaluation script for local messaging LLMs against ShowUp guardrails."""

from __future__ import annotations

import argparse
import itertools
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from showup.domain.enums import RiskBand
from showup.messaging.guardrails import (
    BLOCKED_GUILT_WORDS,
    MAX_WORD_COUNT,
    clean_draft_text,
)
from showup.messaging.ollama_client import OllamaClient
from showup.messaging.prompt import build_draft_prompt

# Curated evaluation scenarios
CUSTOMER_TYPES = [
    ("first_time", RiskBand.LOW, "First-time customer"),
    ("repeat_noshow", RiskBand.HIGH, "Repeat no-show client"),
    ("short_notice", RiskBand.MEDIUM, "Short-notice (<3h) booking"),
    ("next_day", RiskBand.LOW, "Next-day regular booking"),
]

BUSINESSES = [
    ("Haircut & Styling", "Luxe Salon", ["hair", "cut", "styling", "salon", "appointment"]),
    (
        "Dental Checkup",
        "City Dental Clinic",
        ["dental", "checkup", "clinic", "teeth", "appointment"],
    ),
    ("Math Tutoring", "Bright Minds Tutoring", ["math", "tutoring", "session", "lesson", "tutor"]),
    (
        "Bicycle Tune-Up",
        "Apex Cycle Repairs",
        ["bicycle", "bike", "tune-up", "repairs", "service", "appointment"],
    ),
]

NAMES = [
    ("Dan Cole", "Dan"),
    ("Mia Ray", "Mia"),
    ("Aishwarya Venkataraman", "Aishwarya"),
    ("Bartholomew Fitzpatrick", "Bartholomew"),
]

TIMES = [
    ("Today at 4:30 PM", ["today", "4:30", "pm"]),
    ("Tomorrow at 10:00 AM", ["tomorrow", "10:00", "am"]),
    ("Thursday at 2:00 PM", ["thursday", "2:00", "pm"]),
]

INVENTED_FACT_PATTERNS = [
    re.compile(r"[\$£€₹]\s*\d+"),
    re.compile(r"\b\d+\s*(?:dollars|pounds|euros|rupees)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:\d+\s+)?(?:Main|Oak|Maple|High|Market)\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:discount|special\s+offer|promo|%\s*off|free\s+gift)\b", re.IGNORECASE),
]

POLITE_PHRASES = [
    "please",
    "look forward",
    "looking forward",
    "see you",
    "thank",
    "welcome",
    "happy to",
    "glad",
    "reminder",
    "confirming",
    "hello",
    "hi",
]


def check_message(
    text: str,
    client_name: str,
    first_name: str,
    service_name: str,
    business_keywords: list[str],
    time_keywords: list[str],
) -> dict[str, bool]:
    """Execute all 7 validation checks on a drafted message."""
    cleaned = clean_draft_text(text)
    lower = cleaned.lower()

    # 1. Name present (first name or full name)
    name_present = (first_name.lower() in lower) or (client_name.lower() in lower)

    # 2. Time present (at least one key time token)
    time_present = any(tk.lower() in lower for tk in time_keywords)

    # 3. Business or service keyword present
    service_lower = service_name.lower()
    biz_present = (service_lower in lower) or any(bk.lower() in lower for bk in business_keywords)

    # 4. Word count strictly <= MAX_WORD_COUNT (40)
    word_count_ok = len(cleaned.split()) <= MAX_WORD_COUNT

    # 5. Zero guilt or coercive words
    guilt_present = any(re.search(pat, cleaned, re.IGNORECASE) for pat in BLOCKED_GUILT_WORDS)
    zero_guilt_ok = not guilt_present

    # 6. No invented facts (prices, physical street addresses, unsolicited discounts)
    invented_facts = any(pat.search(cleaned) for pat in INVENTED_FACT_PATTERNS)
    no_invented_facts_ok = not invented_facts

    # 7. Polite tone
    polite_ok = any(phrase in lower for phrase in POLITE_PHRASES)

    return {
        "name_present": name_present,
        "time_present": time_present,
        "business_present": biz_present,
        "word_count_limit": word_count_ok,
        "zero_guilt_words": zero_guilt_ok,
        "no_invented_facts": no_invented_facts_ok,
        "polite_tone": polite_ok,
    }


def run_eval(model_name: str, n_samples: int) -> Path:
    """Run evaluation for n_samples scenarios and write markdown report."""
    client = OllamaClient()
    if not client.check_health():
        raise RuntimeError(
            "Local Ollama is offline on http://localhost:11434. Please start Ollama first."
        )

    # Generate cycling scenario combinations
    combinations = list(itertools.product(CUSTOMER_TYPES, BUSINESSES, NAMES, TIMES))
    selected_scenarios = combinations[:n_samples]
    if len(selected_scenarios) < n_samples:
        # Repeat cycle if n_samples > combinations
        repeated = itertools.cycle(combinations)
        selected_scenarios = [next(repeated) for _ in range(n_samples)]

    results: list[dict[str, Any]] = []
    print(f"Starting evaluation of model '{model_name}' on {n_samples} scenarios...")

    for idx, (cust, biz, name, t_info) in enumerate(selected_scenarios, 1):
        cust_label, risk_band, cust_desc = cust
        service_name, biz_name, biz_kw = biz
        full_name, first_name = name
        time_str, time_kw = t_info

        sys_prompt, user_prompt, _ = build_draft_prompt(
            client_name=full_name,
            appointment_time_str=time_str,
            service_name=service_name,
            language_code="en",
            risk_band=risk_band,
        )

        try:
            raw_text = client.generate(
                prompt=user_prompt,
                model=model_name,
                system_prompt=sys_prompt,
            )
        except Exception as e:
            raw_text = f"[ERROR: Generation failed: {e}]"

        checks = check_message(
            text=raw_text,
            client_name=full_name,
            first_name=first_name,
            service_name=service_name,
            business_keywords=biz_kw,
            time_keywords=time_kw,
        )
        all_passed = all(checks.values())

        results.append(
            {
                "idx": idx,
                "scenario": f"{cust_desc} | {biz_name} ({service_name}) | {full_name} | {time_str}",
                "raw_text": clean_draft_text(raw_text),
                "word_count": len(clean_draft_text(raw_text).split()),
                "checks": checks,
                "all_passed": all_passed,
            }
        )
        status_icon = "PASS" if all_passed else "FAIL"
        print(f"[{idx}/{n_samples}] {status_icon}: {cust_label} - {full_name} ({biz_name})")

    # Aggregate metric pass rates
    total = len(results)
    check_keys = [
        ("name_present", "Client Name Present"),
        ("time_present", "Appointment Time Present"),
        ("business_present", "Service/Business Context Present"),
        ("word_count_limit", "Word Count Limit (<= 40 words)"),
        ("zero_guilt_words", "Zero Guilt / Blame Words"),
        ("no_invented_facts", "No Invented Facts (Price/Address/Promo)"),
        ("polite_tone", "Polite Professional Tone"),
    ]

    pass_rates: dict[str, tuple[str, int, float]] = {}
    for key, label in check_keys:
        passed = sum(1 for r in results if r["checks"].get(key, False))
        rate = (passed / total) * 100.0 if total > 0 else 0.0
        pass_rates[key] = (label, passed, rate)

    all_passed_count = sum(1 for r in results if r["all_passed"])
    overall_rate = (all_passed_count / total) * 100.0 if total > 0 else 0.0

    # Write report
    clean_model = model_name.replace(":", "_").replace("/", "_").replace(".", "_")
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"messages_eval_{clean_model}.md"

    md_lines: list[str] = [
        f"# Messaging LLM Evaluation Report: `{model_name}`",
        "",
        f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Model**: `{model_name}`",
        f"- **Total Scenarios Evaluated**: {total}",
        f"- **Perfect Compliance Rate (All Checks Passed)**: **{overall_rate:.1f}%** ({all_passed_count}/{total})",
        "",
        "## Guardrail Pass Rates",
        "",
        "| Guardrail Check | Passed | Total | Pass Rate |",
        "| :--- | :---: | :---: | :---: |",
    ]

    for _key, (label, passed, rate) in pass_rates.items():
        md_lines.append(f"| {label} | {passed} | {total} | **{rate:.1f}%** |")

    md_lines.extend(
        [
            "",
            "## Evaluated Samples & Failures",
            "",
        ]
    )

    failures = [r for r in results if not r["all_passed"]]
    if failures:
        md_lines.append(f"### Guardrail Failures ({len(failures)} total)")
        md_lines.append("")
        for f in failures:
            failed_checks = [
                label for k, (label, _, _) in pass_rates.items() if not f["checks"].get(k, False)
            ]
            md_lines.append(f"#### Sample #{f['idx']}: {f['scenario']}")
            md_lines.append(f"- **Failed Checks**: `{', '.join(failed_checks)}`")
            md_lines.append(f"- **Word Count**: {f['word_count']} words")
            md_lines.append("- **Raw Output**:")
            md_lines.append(f'  > "{f["raw_text"]}"')
            md_lines.append("")
    else:
        md_lines.append("### All samples passed 100% of guardrails! 🎉")
        md_lines.append("")

    md_lines.append("### Sample Passing Output")
    md_lines.append("")
    passes = [r for r in results if r["all_passed"]]
    for p in passes[:3]:
        md_lines.append(f"- **Scenario**: {p['scenario']}")
        md_lines.append(f'  - *Draft ({p["word_count"]} words)*: "{p["raw_text"]}"')

    report_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nEvaluation complete. Report saved to: {report_path.resolve()}")
    print(f"Overall Perfect Pass Rate: {overall_rate:.1f}% ({all_passed_count}/{total})")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate Ollama messaging model against ShowUp guardrails."
    )
    parser.add_argument(
        "--model", type=str, default="llama3.2:3b", help="Ollama model tag to evaluate."
    )
    parser.add_argument("--n", type=int, default=12, help="Number of scenarios to evaluate.")
    args = parser.parse_args()

    run_eval(model_name=args.model, n_samples=args.n)


if __name__ == "__main__":
    main()
