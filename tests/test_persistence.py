import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from build_persistence import SCHEMA, build, digest, require_pair, validate

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/release/persistence"


def test_same_ward_handoff_rebuild_and_source_values(tmp_path):
    actual = build(ROOT, ROOT.parent / "local_elections", tmp_path)
    expected = pq.read_table(RELEASE / "wards_2007_2012.parquet")
    assert actual.equals(expected)
    assert actual.schema.equals(SCHEMA)
    data = actual.to_pandas().set_index("ward_no")
    assert data.body.value_counts().to_dict() == {
        "North Delhi Municipal Corporation": 104,
        "South Delhi Municipal Corporation": 104,
        "East Delhi Municipal Corporation": 64,
    }
    assert data.loc["115", "winner_woman_decision"] == "unresolved"
    assert data.loc["115", "winner_woman_raw"] == "F"
    assert data.winner_woman.isna().sum() == 1
    assert data.loc["111", "winner_woman"] == 1
    assert data.loc["254", "winner_woman"] == 0
    open_wards = data[data.reserved_woman.eq(0)]
    assert len(open_wards) == 134
    assert open_wards.winner_woman.count() == 133
    assert open_wards.groupby("prior_reserved_woman").size().to_dict() == {0: 90, 1: 44}
    assert open_wards.groupby("prior_reserved_woman").winner_woman.sum().to_dict() == {
        0: 2,
        1: 3,
    }
    assert pq.read_table(tmp_path / "ward_links.parquet").num_rows == 272
    differences = (tmp_path / "ward_name_differences.csv").read_text().splitlines()
    assert len(differences) == 17


def test_later_pairs_cannot_silently_use_ward_number():
    require_pair(2007, 2012)
    for pair in [(2012, 2017), (2017, 2022), (2007, 2022)]:
        with pytest.raises(ValueError, match="No validated same-ward link"):
            require_pair(*pair)


def test_invalid_keys_types_and_missing_outcomes_fail():
    table = pq.read_table(RELEASE / "wards_2007_2012.parquet")
    position = table.schema.get_field_index("winner_woman")
    wrong_type = table.set_column(
        position,
        pa.field("winner_woman", pa.bool_()),
        pa.array(
            [None if x is None else bool(x) for x in table.column(position).to_pylist()]
        ),
    )
    with pytest.raises(ValueError, match="Arrow schema"):
        validate(wrong_type)
    rows = table.to_pylist()
    rows[114]["winner_woman"] = 1
    with pytest.raises(ValueError, match="remain missing"):
        validate(pa.Table.from_pylist(rows, schema=SCHEMA))
    rows = table.to_pylist()
    rows[1]["ward_no"] = rows[0]["ward_no"]
    with pytest.raises(ValueError, match="unique wards"):
        validate(pa.Table.from_pylist(rows, schema=SCHEMA))


def test_handoff_and_input_checksums():
    for name, expected in json.loads((RELEASE / "checksums.json").read_text()).items():
        assert digest(RELEASE / name) == expected
    for item in json.loads((RELEASE / "sources.json").read_text()):
        assert digest(ROOT / item["path"]) == item["sha256"]
