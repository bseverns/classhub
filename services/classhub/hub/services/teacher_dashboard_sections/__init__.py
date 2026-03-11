"""Section-focused builders for /teach/class dashboard context."""

from .facilitator_support import build_facilitator_support_snapshot
from .outcomes import (
    build_certificate_eligibility_rows,
    build_outcome_rollup,
    build_outcome_snapshot,
)
from .roster import (
    material_submission_counts,
    submission_counts_by_student,
    support_tag_choices,
    support_tags_by_student,
)
from .shared import detail_int, int_setting

__all__ = [
    "build_certificate_eligibility_rows",
    "build_facilitator_support_snapshot",
    "build_outcome_rollup",
    "build_outcome_snapshot",
    "detail_int",
    "int_setting",
    "material_submission_counts",
    "submission_counts_by_student",
    "support_tag_choices",
    "support_tags_by_student",
]
