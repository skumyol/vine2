from enum import Enum


class Verdict(str, Enum):
    PASS = "PASS"
    NO_IMAGE = "NO_IMAGE"
    ERROR = "ERROR"

    def __str__(self) -> str:
        return self.value


class FieldStatus(str, Enum):
    MATCH = "match"
    NO_SIGNAL = "no_signal"
    CONFLICT = "conflict"
    UNVERIFIED = "unverified"

    def __str__(self) -> str:
        return self.value


class FailReason(str, Enum):
    NO_CANDIDATES = "no_candidates"
    QUALITY_FAILED = "quality_failed"
    IDENTITY_UNVERIFIED = "identity_unverified"
    CONFLICTING_FIELDS = "conflicting_fields"
    PRODUCER_MISMATCH = "producer_mismatch"
    APPELLATION_MISMATCH = "appellation_mismatch"
    VINEYARD_OR_CUVEE_MISMATCH = "vineyard_or_cuvee_mismatch"
    CLASSIFICATION_CONFLICT = "classification_conflict"
    VINTAGE_MISMATCH = "vintage_mismatch"
    UNREADABLE_CORE_IDENTITY = "unreadable_core_identity"
    PIPELINE_NOT_IMPLEMENTED = "pipeline_not_implemented"

    def __str__(self) -> str:
        return self.value


class AnalyzerMode(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"

    def __str__(self) -> str:
        return self.value
