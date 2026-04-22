"""
End-to-end integration tests for the germplasm resolver.

Simulates the MAGIC and CB-tepary sheets from
`/Users/bnbailey/Downloads/Summer2022_Davis stand count_GEMINI.xlsx` —
both use small integer "Line ID" values (1, 2, 3, ...) that mean different
accessions in different experiments. The resolver must keep experiment-scoped
aliases isolated so an import can't accidentally collapse two experiments'
numeric keys onto the same germplasm.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
Run with: pytest tests/integration/test_resolver_end_to_end.py -v -m integration
"""
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


@pytest.fixture
def magic_experiment(setup_real_db):
    from gemini.db.models.experiments import ExperimentModel
    from gemini.db.models.accessions import AccessionModel

    exp = ExperimentModel.create(experiment_name="MAGIC 2022")
    accessions = {}
    for n in (110, 90, 171, 123, 133):
        name = f"MAGIC{n:03d}"
        accessions[name] = AccessionModel.create(accession_name=name)
    return exp, accessions


@pytest.fixture
def tepary_experiment(setup_real_db):
    from gemini.db.models.experiments import ExperimentModel
    from gemini.db.models.accessions import AccessionModel

    exp = ExperimentModel.create(experiment_name="CB-tepary 2022")
    accessions = {
        "CB-46": AccessionModel.create(accession_name="CB-46"),
        "CB-290": AccessionModel.create(accession_name="CB-290"),
    }
    return exp, accessions


class TestExactResolution:

    def test_accession_name_resolves_exact(self, magic_experiment):
        from gemini.api.germplasm_resolver import resolve_germplasm
        exp, accs = magic_experiment

        results = resolve_germplasm(["MAGIC110", "MAGIC090"], experiment_id=exp.id)

        assert len(results) == 2
        assert results[0].match_kind == "accession_exact"
        assert str(results[0].accession_id) == str(accs["MAGIC110"].id)
        assert results[1].match_kind == "accession_exact"
        assert str(results[1].accession_id) == str(accs["MAGIC090"].id)

    def test_case_insensitive_exact_match(self, magic_experiment):
        from gemini.api.germplasm_resolver import resolve_germplasm
        exp, accs = magic_experiment

        # Sheet data often has inconsistent case (Sl-58-6-8-09 vs SL-58-6-8-07).
        results = resolve_germplasm(["magic110", "MAGIC090", "Magic171"], experiment_id=exp.id)
        kinds = [r.match_kind for r in results]
        assert kinds == ["accession_exact"] * 3

    def test_line_exact_match_wins_when_no_accession(self, setup_real_db):
        from gemini.db.models.lines import LineModel
        from gemini.api.germplasm_resolver import resolve_germplasm

        line = LineModel.create(line_name="B73")
        results = resolve_germplasm(["B73"], experiment_id=None)
        assert results[0].match_kind == "line_exact"
        assert str(results[0].line_id) == str(line.id)


class TestAliasResolution:

    def test_experiment_scoped_alias(self, magic_experiment):
        from gemini.api.germplasm_resolver import resolve_germplasm
        from gemini.db.models.accession_aliases import AccessionAliasModel
        exp, accs = magic_experiment

        AccessionAliasModel.create(
            alias="1",
            accession_id=accs["MAGIC110"].id,
            scope="experiment",
            experiment_id=exp.id,
            source="import:Summer2022_Davis.xlsx#MAGIC",
        )

        results = resolve_germplasm(["1"], experiment_id=exp.id)
        assert results[0].match_kind == "alias_experiment"
        assert str(results[0].accession_id) == str(accs["MAGIC110"].id)
        assert results[0].canonical_name == "MAGIC110"

    def test_global_alias(self, setup_real_db):
        from gemini.db.models.accessions import AccessionModel
        from gemini.db.models.accession_aliases import AccessionAliasModel
        from gemini.api.germplasm_resolver import resolve_germplasm

        acc = AccessionModel.create(accession_name="PI-12345")
        AccessionAliasModel.create(
            alias="Othello", accession_id=acc.id, scope="global",
        )

        results = resolve_germplasm(["Othello"], experiment_id=None)
        assert results[0].match_kind == "alias_global"
        assert str(results[0].accession_id) == str(acc.id)

    def test_experiment_alias_preferred_over_global(self, magic_experiment):
        from gemini.db.models.accession_aliases import AccessionAliasModel
        from gemini.db.models.accessions import AccessionModel
        from gemini.api.germplasm_resolver import resolve_germplasm
        exp, accs = magic_experiment

        other = AccessionModel.create(accession_name="GLOBAL-ACC")
        # Global alias "1" → GLOBAL-ACC
        AccessionAliasModel.create(alias="1", accession_id=other.id, scope="global")
        # Experiment alias "1" → MAGIC110
        AccessionAliasModel.create(
            alias="1", accession_id=accs["MAGIC110"].id,
            scope="experiment", experiment_id=exp.id,
        )

        results = resolve_germplasm(["1"], experiment_id=exp.id)
        assert results[0].match_kind == "alias_experiment"
        assert str(results[0].accession_id) == str(accs["MAGIC110"].id)


class TestScopeIsolation:
    """Two experiments should be able to use the same numeric alias
    (`1`, `2`, `3`, ...) without collisions."""

    def test_overlapping_experiment_aliases_do_not_bleed(
        self, magic_experiment, tepary_experiment
    ):
        from gemini.db.models.accession_aliases import AccessionAliasModel
        from gemini.api.germplasm_resolver import resolve_germplasm

        magic_exp, magic_accs = magic_experiment
        tepary_exp, tepary_accs = tepary_experiment

        # "1" in MAGIC means MAGIC110
        AccessionAliasModel.create(
            alias="1", accession_id=magic_accs["MAGIC110"].id,
            scope="experiment", experiment_id=magic_exp.id,
        )
        # "1" in CB-tepary means CB-46
        AccessionAliasModel.create(
            alias="1", accession_id=tepary_accs["CB-46"].id,
            scope="experiment", experiment_id=tepary_exp.id,
        )

        magic_hit = resolve_germplasm(["1"], experiment_id=magic_exp.id)[0]
        tepary_hit = resolve_germplasm(["1"], experiment_id=tepary_exp.id)[0]

        assert magic_hit.match_kind == "alias_experiment"
        assert str(magic_hit.accession_id) == str(magic_accs["MAGIC110"].id)

        assert tepary_hit.match_kind == "alias_experiment"
        assert str(tepary_hit.accession_id) == str(tepary_accs["CB-46"].id)

        # And neither resolves without an experiment context.
        loose = resolve_germplasm(["1"], experiment_id=None)[0]
        assert loose.match_kind == "unresolved"


class TestUnresolvedAndMixed:

    def test_unknown_name_is_unresolved(self, magic_experiment):
        from gemini.api.germplasm_resolver import resolve_germplasm
        exp, _ = magic_experiment
        results = resolve_germplasm(["MAGIC11O"], experiment_id=exp.id)  # letter-O typo
        assert results[0].match_kind == "unresolved"
        assert results[0].accession_id is None
        assert results[0].line_id is None

    def test_mixed_input_preserves_order(self, magic_experiment):
        from gemini.db.models.accession_aliases import AccessionAliasModel
        from gemini.api.germplasm_resolver import resolve_germplasm
        exp, accs = magic_experiment

        AccessionAliasModel.create(
            alias="1", accession_id=accs["MAGIC110"].id,
            scope="experiment", experiment_id=exp.id,
        )
        inputs = ["MAGIC090", "1", "ghost", "MAGIC123"]
        results = resolve_germplasm(inputs, experiment_id=exp.id)

        assert [r.input_name for r in results] == inputs
        assert [r.match_kind for r in results] == [
            "accession_exact", "alias_experiment", "unresolved", "accession_exact",
        ]


class TestUniqueConstraint:
    """Scope uniqueness: two aliases with the same (scope, experiment_id,
    lower(alias)) must conflict."""

    def test_duplicate_within_experiment_rejected(self, magic_experiment):
        from gemini.db.models.accession_aliases import AccessionAliasModel
        from gemini.db.core.base import db_engine
        from sqlalchemy.exc import IntegrityError
        exp, accs = magic_experiment

        AccessionAliasModel.create(
            alias="1", accession_id=accs["MAGIC110"].id,
            scope="experiment", experiment_id=exp.id,
        )
        with pytest.raises(IntegrityError):
            with db_engine.get_session() as session:
                session.execute(text(
                    "INSERT INTO gemini.accession_aliases "
                    "(alias, accession_id, scope, experiment_id) "
                    "VALUES (:a, :acc, 'experiment', :exp)"
                ), {"a": "1", "acc": str(accs["MAGIC090"].id), "exp": str(exp.id)})

    def test_same_alias_in_different_experiments_allowed(
        self, magic_experiment, tepary_experiment
    ):
        from gemini.db.models.accession_aliases import AccessionAliasModel
        magic_exp, magic_accs = magic_experiment
        tepary_exp, tepary_accs = tepary_experiment

        a = AccessionAliasModel.create(
            alias="1", accession_id=magic_accs["MAGIC110"].id,
            scope="experiment", experiment_id=magic_exp.id,
        )
        b = AccessionAliasModel.create(
            alias="1", accession_id=tepary_accs["CB-46"].id,
            scope="experiment", experiment_id=tepary_exp.id,
        )
        assert a.id != b.id

    def test_check_constraint_requires_exactly_one_target(self, magic_experiment):
        from gemini.db.core.base import db_engine
        from sqlalchemy.exc import IntegrityError

        # Neither accession_id nor line_id set → CHECK violation.
        with pytest.raises(IntegrityError):
            with db_engine.get_session() as session:
                session.execute(text(
                    "INSERT INTO gemini.accession_aliases (alias, scope) "
                    "VALUES ('orphan', 'global')"
                ))
