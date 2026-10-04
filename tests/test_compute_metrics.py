from scripts.compute_metrics import summarize


def test_metrics_known_fabricated_dataset():
    baseline = [
        {"task_id": "a", "hidden_passed": True, "tokens": 10, "duration": 2, "safety": False},
        {"task_id": "b", "hidden_passed": False, "tokens": 20, "duration": 4, "safety": True},
    ]
    sessions = [
        {"task_id": "a", "status": "succeeded", "attempts": [
            {"phase": "candidate", "visible": True, "hidden": True, "selected": True, "tokens": 10, "duration": 1, "safety": False},
            {"phase": "candidate", "visible": True, "hidden": False, "selected": False, "tokens": 10, "duration": 1, "safety": False},
        ]},
        {"task_id": "b", "status": "succeeded", "attempts": [
            {"phase": "candidate", "visible": False, "hidden": False, "selected": True, "tokens": 10, "duration": 1, "safety": False},
            {"phase": "candidate", "visible": False, "hidden": True, "selected": False, "tokens": 10, "duration": 1, "safety": False},
            {"phase": "repair", "visible": None, "hidden": True, "selected": False, "tokens": 10, "duration": 1, "safety": True},
        ]},
    ]
    result = summarize(baseline, sessions)
    assert result["baseline_task_success_rate"] == 0.5
    assert result["verified_task_success_rate"] == 1.0
    assert result["verification_accuracy"] == 0.5
    assert result["verification_false_positive_rate"] == 0.5
    assert result["verification_false_negative_rate"] == 0.5
    assert result["recovery_success_rate"] == 1.0
    assert result["replanning_efficiency"] == 1.0
    assert result["baseline_avg_tokens"] == 15.0
    assert result["verified_avg_tokens"] == 25.0
    assert result["safety_violation_rate"] == 2 / 7


def test_false_positive_rate_is_blank_when_no_candidate_passes_visible_tests():
    result = summarize([], [{"task_id": "none", "status": "failed", "attempts": [
        {"phase": "candidate", "visible": False, "hidden": False, "selected": True,
         "tokens": 1, "duration": 1, "safety": False},
    ]}])

    assert result["verification_false_positive_rate"] is None


def test_verification_rates_use_the_requested_candidate_denominators():
    result = summarize([], [{"task_id": "mix", "status": "failed", "attempts": [
        {"phase": "candidate", "visible": True, "hidden": True, "selected": True,
         "tokens": 1, "duration": 1, "safety": False},
        {"phase": "candidate", "visible": True, "hidden": False, "selected": False,
         "tokens": 1, "duration": 1, "safety": False},
        {"phase": "candidate", "visible": False, "hidden": True, "selected": False,
         "tokens": 1, "duration": 1, "safety": False},
        {"phase": "candidate", "visible": False, "hidden": False, "selected": False,
         "tokens": 1, "duration": 1, "safety": False},
    ]}])

    assert result["verification_accuracy"] == 0.5
    assert result["verification_false_negative_rate"] == 0.5
    assert result["verification_false_positive_rate"] == 0.5


def test_aggregate_verification_rates_pool_candidates_instead_of_averaging_tasks():
    task_rows = [
        {"task_id": "small", "status": "failed", "attempts": [
            {"phase": "candidate", "visible": True, "hidden": False, "selected": True,
             "tokens": 1, "duration": 1, "safety": False},
        ]},
        {"task_id": "large", "status": "failed", "attempts": [
            {"phase": "candidate", "visible": True, "hidden": True, "selected": True,
             "tokens": 1, "duration": 1, "safety": False},
        ] * 9},
    ]

    small = summarize([], [task_rows[0]])
    large = summarize([], [task_rows[1]])
    aggregate = summarize([], task_rows)

    assert small["verification_false_positive_rate"] == 1.0
    assert large["verification_false_positive_rate"] == 0.0
    assert aggregate["verification_false_positive_rate"] == 0.1
    assert aggregate["verification_false_positive_rate"] != (
        small["verification_false_positive_rate"] + large["verification_false_positive_rate"]
    ) / 2
