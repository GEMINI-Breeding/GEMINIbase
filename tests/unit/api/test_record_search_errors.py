"""Record search/filter must raise on a DB error, not yield None.

A None in the stream crashed consumers with an AttributeError that hid the
real error (`None.model_dump()` in the NDJSON stream, `r.record_info` in
the analysis endpoints). TraitRecord/SensorRecord already re-raise.
"""
from datetime import datetime
from unittest.mock import patch

import pytest

from gemini.api.dataset_record import DatasetRecord
from gemini.api.model_record import ModelRecord
from gemini.api.procedure_record import ProcedureRecord
from gemini.api.script_record import ScriptRecord

CASES = [
    (DatasetRecord, "dataset", "Dataset", {"dataset_name": "d"}),
    (ModelRecord, "model", "Model", {"model_name": "m"}),
    (ProcedureRecord, "procedure", "Procedure", {"procedure_name": "p"}),
    (ScriptRecord, "script", "Script", {"script_name": "s"}),
]
IDS = [c[0].__name__ for c in CASES]


@pytest.mark.parametrize("cls,module,prefix,search_kwargs", CASES, ids=IDS)
def test_search_raises_on_db_error(cls, module, prefix, search_kwargs):
    with patch(f"gemini.api.{module}_record.{prefix}RecordsIMMVModel.stream",
               side_effect=RuntimeError("db connection lost")):
        with pytest.raises(RuntimeError, match="db connection lost"):
            list(cls.search(**search_kwargs))


@pytest.mark.parametrize("cls,module,prefix,search_kwargs", CASES, ids=IDS)
def test_filter_raises_on_db_error(cls, module, prefix, search_kwargs):
    with patch(f"gemini.api.{module}_record.{prefix}RecordModel.filter_records",
               side_effect=RuntimeError("db connection lost")):
        with pytest.raises(RuntimeError, match="db connection lost"):
            list(cls.filter(start_timestamp=datetime(2024, 1, 1)))
