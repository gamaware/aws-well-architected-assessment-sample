"""Figures derived from the synthetic exports, checked against counts made by hand from the CSV files."""

from __future__ import annotations

import pytest

from wa_assess import metrics


@pytest.mark.parametrize(
    ("value", "places", "expected"),
    [(2.25, 1, 2.3), (2.35, 1, 2.4), (10.6383, 1, 10.6), (69.5, 0, 70), (70.4, 0, 70), (0.5, 0, 1)],
)
def test_round_half_up(value, places, expected):
    assert metrics.round_half_up(value, places) == expected


def test_delivery_figures_match_the_deployment_export(repo_root):
    figures = metrics.compute(repo_root, window_days=90)["delivery"]
    # 47 rows; DEP-005, DEP-019 and DEP-027 rolled back; DEP-012 and DEP-031 failed.
    assert figures["deployments"] == 47
    assert figures["rollbacks"] == 3
    assert figures["failed"] == 2
    assert figures["change_failure_rate_pct"] == 10.6  # 5 / 47
    assert figures["deploys_per_week"] == 3.7  # 47 / (90 / 7)


def test_incident_figures_match_the_incident_export(repo_root):
    figures = metrics.compute(repo_root, window_days=90)["incidents"]
    assert figures == {
        "total": 7,
        "customer_detected": 3,  # INC-101, INC-104, INC-106
        "postmortems": 2,  # INC-103, INC-106
        "median_minutes_to_detect": 30,  # sorted: 4 6 18 30 38 42 55
        "median_minutes_to_restore": 70,  # sorted: 15 25 40 70 95 120 185
        "longest_minutes_to_restore": 185,
        "longest_incident": "INC-106",
    }


def test_access_key_figures_match_the_credential_report(repo_root):
    figures = metrics.compute(repo_root, window_days=90)["access_keys"]
    assert figures == {
        "active_keys": 3,
        "active_over_90_days": 3,  # 412, 233 and 806 days
        "oldest_age_days": 806,
        "console_users_without_mfa": 1,  # ops-admin-2
    }


def test_fill_replaces_known_placeholders():
    figures = {"delivery": {"rollbacks": 3}}
    assert metrics.fill("{delivery.rollbacks} rollbacks", figures) == "3 rollbacks"


def test_fill_rejects_unknown_placeholders():
    with pytest.raises(KeyError, match=r"delivery\.nope"):
        metrics.fill("{delivery.nope}", {"delivery": {}})


def test_unknown_export_values_are_rejected(tmp_path):
    export = tmp_path / "deployments.csv"
    export.write_text("deploy_id,day,service,lead_time_hours,outcome,incident_id\nDEP-1,1,web,2.0,sucess,\n")
    with pytest.raises(ValueError, match="outcome is 'sucess'"):
        metrics.delivery(export, window_days=7)
