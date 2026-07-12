# Non-combat policy-learning pilot

Label mode: current
Source commit: f321cb05a40c808d3abfba8b977dfe8988b8ee47

Formal non-combat RL: blocked
Live policy promotion: blocked
Off-policy evaluation: unsupported

## Limitations
Missing trajectories, target mappings, unknown behavior propensities, and contextual alternative-action overlap block off-policy evaluation.
Aggregate candidate counts do not establish contextual alternative-action overlap.
Outcomes are diagnostics only and are not supervised targets.

## Dataset exclusions
{
  "missing_candidates": 18,
  "missing_trajectory_group": 965
}

## Category support
### shop
{
  "blocking_reasons": [],
  "evaluable": true,
  "held_out_trajectory_count": 5,
  "train_trajectory_count": 4
}

### event
{
  "blocking_reasons": [],
  "evaluable": true,
  "held_out_trajectory_count": 5,
  "train_trajectory_count": 5
}

### route
{
  "blocking_reasons": [],
  "evaluable": true,
  "held_out_trajectory_count": 6,
  "train_trajectory_count": 8
}

### card_reward
{
  "blocking_reasons": [],
  "evaluable": true,
  "held_out_trajectory_count": 6,
  "train_trajectory_count": 8
}

## Split counts
{
  "groups": {
    "test": [
      "run:1783789975",
      "run:1783789391",
      "run:1783788934",
      "run:1783788747"
    ],
    "train": [
      "run:1783788512",
      "run:1783789260",
      "run:1783789186",
      "run:1783788319",
      "run:1783789058",
      "run:1783787727",
      "run:1783789651",
      "run:1783790044"
    ],
    "validation": [
      "run:1783787808",
      "run:1783788034"
    ]
  },
  "split_sample_counts": {
    "test": 157,
    "train": 229,
    "validation": 84
  },
  "support": {
    "blocked": false,
    "blocking_reasons": [],
    "minimum_trajectory_count": 10,
    "split_sample_counts": {
      "test": 157,
      "train": 229,
      "validation": 84
    },
    "split_trajectory_counts": {
      "test": 4,
      "train": 8,
      "validation": 2
    },
    "trajectory_count": 14
  }
}

## Outcome diagnostics
{
  "dataset": {
    "rows": {
      "join_status": {
        "matched": 470
      },
      "victory": {
        "false": 470,
        "true": 0,
        "unknown": 0
      }
    },
    "trajectories": {
      "join_status": {
        "matched": 14
      },
      "victory": {
        "false": 14,
        "true": 0,
        "unknown": 0
      }
    }
  },
  "support": {
    "rows": {
      "join_status": {
        "matched": 470
      },
      "victory": {
        "false": 470,
        "true": 0,
        "unknown": 0
      }
    },
    "trajectories": {
      "join_status": {
        "matched": 14
      },
      "victory": {
        "false": 14,
        "true": 0,
        "unknown": 0
      }
    }
  }
}

## Held-out metrics

### Validation
{
  "candidate_legality": 1.0,
  "frequency_reference_top1_agreement": 0.6547619047619048,
  "mean_target_cross_entropy": 0.42391512652512314,
  "model_reference_top1_agreement": 0.7857142857142857,
  "per_category_counts": {
    "card_reward": 14,
    "event": 13,
    "route": 52,
    "shop": 5
  },
  "sample_count": 84,
  "top_confidence_ece": 0.05927940883806773
}

### Test
{
  "candidate_legality": 1.0,
  "frequency_reference_top1_agreement": 0.6942675159235668,
  "mean_target_cross_entropy": 0.5068756737822403,
  "model_reference_top1_agreement": 0.7707006369426752,
  "per_category_counts": {
    "card_reward": 24,
    "event": 31,
    "route": 92,
    "shop": 10
  },
  "sample_count": 157,
  "top_confidence_ece": 0.07899013769095112
}
