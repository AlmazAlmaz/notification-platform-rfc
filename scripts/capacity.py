"""Reproduce docs/03-capacity.md using standard-library Decimal arithmetic.

Run from the repository root: python scripts/capacity.py [--json]
These are design assumptions, not measured system performance or vendor prices.
JSON values are decimal strings to preserve exact values across consumers.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, getcontext


getcontext().prec = 28
D = Decimal


def calculate() -> dict[str, Decimal]:
    dau, mau, ccu = D(3_000_000), D(10_000_000), D(300_000)
    seconds_day = D(86_400)
    txn_day, service_day, marketing_day = dau * 2, dau * 3, dau * 5
    total_day = txn_day + service_day + marketing_day
    critical_budget, service_budget, marketing_budget = D(2000), D(2500), D(3500)
    push_retry, sms_fallback, sms_retry, email_after_sms = map(
        D, ("0.02", "0.08", "0.02", "0.10")
    )
    push_factor = 1 + push_retry
    sms_factor = sms_fallback * (1 + sms_retry)
    email_factor = sms_fallback * email_after_sms
    attempt_factor = push_factor + sms_factor + email_factor
    critical_attempts_day = txn_day * attempt_factor
    total_attempts_day = critical_attempts_day + service_day + marketing_day
    logical_budget = critical_budget + service_budget + marketing_budget

    push_peak = critical_budget * push_factor + service_budget * D("0.95") + marketing_budget * D("0.8")
    sms_peak = critical_budget * sms_factor
    email_peak = critical_budget * email_factor + service_budget * D("0.05") + marketing_budget * D("0.2")
    attempts_peak = push_peak + sms_peak + email_peak
    concurrency = push_peak * D("0.2") + sms_peak * D("0.5") + email_peak * D("0.4")

    kib, gb, reserve, replicas = D(1024), D(10**9), D("1.3"), D(3)
    metadata_day_gb = txn_day * (D("1.5") + attempt_factor * D("0.8")) * kib / gb
    journal_day_gb = txn_day * 8 * D("0.3") * kib / gb
    hot_gb = metadata_day_gb * 30 + journal_day_gb * 7
    hot_primary_gb = hot_gb * reserve
    hot_replicated_gb = hot_primary_gb * replicas
    tombstone_logical_gb = txn_day * 90 * 96 / gb
    tombstone_physical_gb = tombstone_logical_gb * reserve * replicas
    total_ledger_physical_gb = hot_replicated_gb + tombstone_physical_gb
    archive_gb = journal_day_gb * (365 - 7) * D("0.3")
    row_changes = critical_budget * (1 + attempt_factor + 8 + 5)

    sms_provider_quota, outage_seconds = D(2200), D(600)
    backlog = critical_budget * outage_seconds
    recovery_logical_rate = D(3000)
    recovery_sms_rate = recovery_logical_rate * (1 + sms_retry)
    recovery_seconds = backlog / (recovery_logical_rate - critical_budget)
    one_provider_logical_rate = sms_provider_quota / (1 + sms_retry)
    one_provider_recovery_minutes = backlog / (one_provider_logical_rate - critical_budget) / 60
    outage_sms_attempts = backlog * (1 + sms_retry)

    push_price, sms_price, email_price = D("0.001"), D(3), D("0.02")
    normal_cost = txn_day * (push_factor * push_price + sms_factor * sms_price + email_factor * email_price)
    all_sms_cost = txn_day * sms_price
    temporal_day_gb = txn_day * 25 * 1000 / gb

    report = {
        "daily_transactional": txn_day,
        "daily_service": service_day,
        "daily_marketing_candidates": marketing_day,
        "daily_all": total_day,
        "average_transactional_per_second": txn_day / seconds_day,
        "average_service_per_second": service_day / seconds_day,
        "average_marketing_per_second": marketing_day / seconds_day,
        "average_all_per_second": total_day / seconds_day,
        "burst_20x_all_per_second": total_day / seconds_day * 20,
        "logical_admission_budget_per_second": logical_budget,
        "campaign_1m_600seconds_per_second": D(1_000_000) / 600,
        "extra_campaign_plus_background_marketing_peak": marketing_day / seconds_day * 20 + D(1_000_000) / 600,
        "mau_interpretation_daily": mau * 10,
        "mau_interpretation_average_per_second": mau * 10 / seconds_day,
        "mau_interpretation_20x_peak": mau * 10 / seconds_day * 20,
        "critical_attempt_factor": attempt_factor,
        "critical_attempts_daily": critical_attempts_day,
        "critical_push_attempts_daily": txn_day * push_factor,
        "critical_sms_attempts_daily": txn_day * sms_factor,
        "critical_email_attempts_daily": txn_day * email_factor,
        "all_attempts_daily": total_attempts_day,
        "all_attempts_average_per_second": total_attempts_day / seconds_day,
        "global_attempt_factor": total_attempts_day / total_day,
        "normal_peak_push_per_second": push_peak,
        "normal_peak_sms_per_second": sms_peak,
        "normal_peak_email_per_second": email_peak,
        "normal_peak_all_attempts_per_second": attempts_peak,
        "normal_concurrency_mean": concurrency,
        "logical_capacity_n_minus_one": D(4000) * (3 - 1),
        "attempt_capacity_n_minus_one": D(5000) * (3 - 1),
        "callback_300k_over_10seconds_per_second": ccu / 10,
        "metadata_gb_daily": metadata_day_gb,
        "journal_gb_daily": journal_day_gb,
        "hot_metadata30d_journal7d_logical_gb": hot_gb,
        "hot_with_reserve_one_copy_gb": hot_primary_gb,
        "hot_with_reserve_three_copies_gb": hot_replicated_gb,
        "tombstones90d_logical_gb": tombstone_logical_gb,
        "tombstones90d_reserved_three_copies_gb": tombstone_physical_gb,
        "total_ledger_and_tombstones_physical_gb": total_ledger_physical_gb,
        "primary_hot_with_tombstones_8shards_gb": (hot_primary_gb + tombstone_logical_gb * reserve) / 8,
        "archive_days8_to365_compressed_gb": archive_gb,
        "kafka_critical7d_rf3_gb": txn_day * kib * 7 * replicas / gb,
        "kafka_all7d_rf3_gb": total_day * kib * 7 * replicas / gb,
        "temporal25events_1kb_gb_daily": temporal_day_gb,
        "temporal3days_logical_gb": temporal_day_gb * 3,
        "temporal3days_three_copies_gb": temporal_day_gb * 3 * replicas,
        "temporal_history_events_per_second": critical_budget * 25,
        "critical_row_changes_per_second": row_changes,
        "critical_row_changes_per_second_per_8shards": row_changes / 8,
        "preferences_logical_gb": mau * kib / gb,
        "push_tokens_logical_gb": mau * 2 * 256 / gb,
        "push_outage_sms_requests_per_second": critical_budget * (1 + sms_retry),
        "all_channels_10minute_outage_backlog": backlog,
        "recovery_sms_requests_per_second": recovery_sms_rate,
        "recovery_two_providers_minutes": recovery_seconds / 60,
        "one_provider_max_logical_sms_per_second": one_provider_logical_rate,
        "recovery_one_provider_minutes": one_provider_recovery_minutes,
        "normal_critical_cost_rub_daily": normal_cost,
        "all_sms_cost_rub_daily_before_retries": all_sms_cost,
        "push_first_cost_saving_percent": (1 - normal_cost / all_sms_cost) * 100,
        "push_outage_10minutes_sms_attempts": outage_sms_attempts,
        "push_outage_10minutes_sms_cost_rub": outage_sms_attempts * sms_price,
        "sms_fallback_1percentagepoint_saving_rub_daily": txn_day * D("0.01") * (1 + sms_retry) * sms_price,
    }

    # Check arithmetic and the capacity assumptions actually claimed in the text.
    assert report["daily_all"] == 30_000_000
    assert attempt_factor == D("1.1096")
    assert critical_attempts_day == 6_657_600
    assert report["global_attempt_factor"] == D("1.02192")
    assert attempts_peak == D("8219.2")
    assert concurrency == D("1861")
    assert attempts_peak < report["attempt_capacity_n_minus_one"]
    assert logical_budget == report["logical_capacity_n_minus_one"]
    assert sms_provider_quota > report["push_outage_sms_requests_per_second"]
    assert recovery_sms_rate < 2 * sms_provider_quota
    assert one_provider_logical_rate > critical_budget
    assert hot_gb == D("543.3163776")
    assert archive_gb == D("1583.67744")
    assert total_ledger_physical_gb == D("2321.10987264")
    assert normal_cost == 1_475_880
    assert report["recovery_two_providers_minutes"] == 20
    assert abs(one_provider_recovery_minutes - D("127.5")) < D("0.000000001")
    assert report["temporal3days_three_copies_gb"] == 1350
    assert report["mau_interpretation_20x_peak"] > logical_budget
    return report


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output exact decimals as JSON strings")
    args = parser.parse_args()
    report = calculate()
    values = {key: decimal_text(value) for key, value in report.items()}
    if args.json:
        print(json.dumps(values, indent=2, ensure_ascii=True))
    else:
        print("Design assumptions only; arithmetic assertions passed.")
        for key, value in values.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
