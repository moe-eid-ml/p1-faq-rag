from typing import List, Iterable, Dict

def _to_set(xs: Iterable[int]) -> set:
    return set(xs) if xs is not None else set()

def precision_at_k(gt_ids: Iterable[int], pred_ids: Iterable[int], k: int = 5) -> float:
    """P@K = |top-K ∩ GT| / K (or / len(pred_ids) if shorter than K)."""
    gt, preds = _to_set(gt_ids), list(pred_ids)[:k]
    denom = max(1, min(k, len(preds)))
    return len(_to_set(preds) & gt) / denom

def recall_at_k(gt_ids: Iterable[int], pred_ids: Iterable[int], k: int = 5) -> float:
    """R@K = |top-K ∩ GT| / |GT|."""
    gt, preds = _to_set(gt_ids), list(pred_ids)[:k]
    if len(gt) == 0:
        return 1.0  # vacuously perfect recall if no ground-truth
    return len(_to_set(preds) & gt) / len(gt)

def evaluate_run(ground_truth: List[Iterable[int]], predictions: List[Iterable[int]], k: int = 5) -> Dict[str, float]:
    """Macro-average P@K and R@K over queries.
    ground_truth[i] = iterable of correct doc ids for query i
    predictions[i]  = iterable of predicted doc ids ranked desc for query i
    """
    assert len(ground_truth) == len(predictions), "GT and predictions length mismatch"
    ps, rs = [], []
    for gt, pred in zip(ground_truth, predictions):
        ps.append(precision_at_k(gt, pred, k))
        rs.append(recall_at_k(gt, pred, k))
    return {
        "queries": len(ground_truth),
        "p_at_k": sum(ps)/len(ps) if ps else 0.0,
        "r_at_k": sum(rs)/len(rs) if rs else 0.0,
        "k": k,
    }
