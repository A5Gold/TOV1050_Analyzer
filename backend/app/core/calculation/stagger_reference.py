from app.core.calculation.stagger_metadata import SupportPoint
from app.core.calculation.stagger_types import ResolvedReference, SelectedSummaryRecord


def resolve_reference_points(
    record: SelectedSummaryRecord,
    supports: list[SupportPoint],
) -> ResolvedReference:
    ordered = sorted(supports, key=lambda item: item.chainage)
    if not ordered:
        return ResolvedReference(
            chi=record.max_location,
            spt_a=None,
            spt_i=None,
            spt_b=None,
            span_ai=None,
            span_ib=None,
        )
    candidate_indexes = [index for index in range(1, len(ordered) - 1)]
    if candidate_indexes:
        nearest_index = min(
            candidate_indexes,
            key=lambda index: abs(ordered[index].chainage - record.max_location),
        )
    else:
        nearest_index = min(
            range(len(ordered)),
            key=lambda index: abs(ordered[index].chainage - record.max_location),
        )

    spt_i = ordered[nearest_index].chainage
    spt_a = ordered[nearest_index - 1].chainage if nearest_index > 0 else None
    spt_b = ordered[nearest_index + 1].chainage if nearest_index + 1 < len(ordered) else None
    span_ai = abs(spt_i - spt_a) if spt_a is not None else None
    span_ib = abs(spt_b - spt_i) if spt_b is not None else None

    return ResolvedReference(
        chi=record.max_location,
        spt_a=spt_a,
        spt_i=spt_i,
        spt_b=spt_b,
        span_ai=span_ai,
        span_ib=span_ib,
    )
