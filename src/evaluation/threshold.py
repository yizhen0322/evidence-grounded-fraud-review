"""Select a detector threshold on validation scores, then freeze it."""

import numpy as np
from sklearn.metrics import precision_recall_curve


def select_threshold_max_f1(y_val, val_scores) -> float:
    """Return the validation threshold with the highest measured F1 score."""
    if np.asarray(val_scores).size == 0:
        raise ValueError("cannot select a threshold from empty validation scores")

    precision, recall, thresholds = precision_recall_curve(y_val, val_scores)
    if thresholds.size == 0:
        raise ValueError("cannot select a threshold from empty validation scores")

    # precision_recall_curve returns one extra terminal precision/recall point
    # that has no corresponding threshold.
    precision_at_threshold = precision[:-1]
    recall_at_threshold = recall[:-1]
    denominator = np.clip(
        precision_at_threshold + recall_at_threshold,
        1e-12,
        None,
    )
    f1 = 2 * precision_at_threshold * recall_at_threshold / denominator
    return float(thresholds[int(np.argmax(f1))])
