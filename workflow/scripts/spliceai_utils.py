"""SpliceAI parsing and deterministic event-selection helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass

EVENT_FIELDS = {
    "acceptor_gain": ("ds_ag", "dp_ag"),
    "acceptor_loss": ("ds_al", "dp_al"),
    "donor_gain": ("ds_dg", "dp_dg"),
    "donor_loss": ("ds_dl", "dp_dl"),
}


@dataclass(frozen=True)
class SpliceAIPrediction:
    """One allele/gene prediction from the SpliceAI INFO field."""

    allele: str
    gene: str
    ds_ag: float
    ds_al: float
    ds_dg: float
    ds_dl: float
    dp_ag: int
    dp_al: int
    dp_dg: int
    dp_dl: int

    @property
    def maximum(self) -> float:
        """Return the maximum delta score."""
        return max(self.ds_ag, self.ds_al, self.ds_dg, self.ds_dl)

    @property
    def events(self) -> tuple[str, ...]:
        """Return every event tied for the maximum score in stable order."""
        return tuple(event for event, (score, _) in EVENT_FIELDS.items() if getattr(self, score) == self.maximum)

    @property
    def delta_positions(self) -> tuple[int, ...]:
        """Return delta positions aligned with :attr:`events`."""
        return tuple(getattr(self, EVENT_FIELDS[event][1]) for event in self.events)

    def as_row(self, position: int) -> dict[str, str]:
        """Serialize the prediction with aligned event and genomic-position fields."""
        row = {key: str(value) for key, value in asdict(self).items()}
        row.update(
            {
                "spliceai_max": format(self.maximum, ".6g"),
                "spliceai_event": ";".join(self.events),
                "spliceai_delta_position": ";".join(str(value) for value in self.delta_positions),
                "predicted_site_position": ";".join(str(position + value) for value in self.delta_positions),
                "predicted_site_ag": str(position + self.dp_ag),
                "predicted_site_al": str(position + self.dp_al),
                "predicted_site_dg": str(position + self.dp_dg),
                "predicted_site_dl": str(position + self.dp_dl),
                "spliceai_status": "scored",
                "spliceai_missing_reason": "",
            }
        )
        return row


def _parse_score(value: str) -> float:
    if value in {"", "."}:
        raise ValueError("missing delta score")
    score = float(value)
    if not 0 <= score <= 1:
        raise ValueError(f"delta score outside [0, 1]: {value}")
    return score


def _parse_position(value: str) -> int:
    if value in {"", "."}:
        raise ValueError("missing delta position")
    return int(value)


def parse_spliceai_entry(entry: str) -> SpliceAIPrediction:
    """Parse one pipe-delimited SpliceAI annotation."""
    values = entry.split("|")
    if len(values) != 10:
        raise ValueError(f"expected 10 SpliceAI fields, found {len(values)}")
    return SpliceAIPrediction(
        allele=values[0],
        gene=values[1],
        ds_ag=_parse_score(values[2]),
        ds_al=_parse_score(values[3]),
        ds_dg=_parse_score(values[4]),
        ds_dl=_parse_score(values[5]),
        dp_ag=_parse_position(values[6]),
        dp_al=_parse_position(values[7]),
        dp_dg=_parse_position(values[8]),
        dp_dl=_parse_position(values[9]),
    )


def parse_spliceai_info(value: str | None) -> tuple[list[SpliceAIPrediction], list[str]]:
    """Parse a comma-delimited INFO value, returning predictions and errors."""
    predictions: list[SpliceAIPrediction] = []
    errors: list[str] = []
    if not value or value == ".":
        return predictions, errors
    for entry in value.split(","):
        try:
            predictions.append(parse_spliceai_entry(entry))
        except (TypeError, ValueError) as exc:
            errors.append(f"{entry}: {exc}")
    return predictions, errors


def is_supported_variant(ref: str, alt: str) -> bool:
    """Return whether the local SpliceAI CLI supports the normalized allele."""
    bases = set("ACGT")
    return bool(
        ref and alt and set(ref.upper()) <= bases and set(alt.upper()) <= bases and (len(ref) == 1 or len(alt) == 1)
    )


def strongest_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """Return all scored rows tied for the maximum score."""
    scored = [
        row for row in rows if row.get("spliceai_status") == "scored" and row.get("spliceai_max") not in {"", None}
    ]
    if not scored:
        return []
    maximum = max(float(row["spliceai_max"]) for row in scored)
    return [row for row in scored if float(row["spliceai_max"]) == maximum]
