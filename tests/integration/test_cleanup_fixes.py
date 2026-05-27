"""Integration tests for the three cleanup-pipeline fixes landed alongside
the 2026-05-18 dev-DB sweep:

  1. ``jobs.experiment_id`` has an ``ON DELETE CASCADE`` FK so jobs
     don't outlive their experiment (migration 0008).
  2. ``Experiment.delete()`` also sweeps accessions reachable only via
     a now-orphan study's ``genotyping_study_samples`` rows.
  3. ``DELETE /api/e2e_cleanup`` surfaces per-entity failures and
     returns HTTP 500 when any delete failed, instead of reporting
     success with empty counts.

These hit the real test DB — no mocks.
"""
import uuid

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


# ============================================================
# Fix 1: jobs.experiment_id FK with ON DELETE CASCADE
# ============================================================

class TestJobsExperimentFK:

    def test_fk_constraint_exists(self, db_engine):
        """The FK that 0008 added must be present after schema init."""
        with db_engine.get_session() as session:
            row = session.execute(text("""
                SELECT pg_get_constraintdef(oid) AS constraint_def
                FROM pg_constraint
                WHERE conrelid = 'gemini.jobs'::regclass
                  AND contype = 'f'
                  AND pg_get_constraintdef(oid) LIKE '%experiment_id%'
            """)).first()
        assert row is not None, "No FK constraint on jobs.experiment_id"
        constraint_def = row.constraint_def
        assert "REFERENCES gemini.experiments(id)" in constraint_def or \
               "REFERENCES experiments(id)" in constraint_def
        assert "ON DELETE CASCADE" in constraint_def

    def test_deleting_experiment_cascades_to_jobs(self, setup_real_db):
        """A job pointing at an experiment is removed when that
        experiment is dropped. Before the FK existed, jobs were
        stranded with a dangling experiment_id."""
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.jobs import JobModel
        from gemini.db.core.base import db_engine

        exp = ExperimentModel.get_or_create(experiment_name="cascade-exp")
        job_id = uuid.uuid4()
        with db_engine.get_session() as session:
            session.execute(text(
                "INSERT INTO gemini.jobs (id, job_type, status, experiment_id) "
                "VALUES (:id, 'RUN_ODM', 'COMPLETED', :eid)"
            ), {"id": str(job_id), "eid": str(exp.id)})
            session.commit()

        # Sanity: the job exists.
        with db_engine.get_session() as session:
            assert session.execute(text(
                "SELECT count(*) FROM gemini.jobs WHERE id = :id"
            ), {"id": str(job_id)}).scalar() == 1

        # Drop the experiment via the raw FK path (the high-level
        # Experiment.delete() cascade also runs ``jobs`` SET-NULL
        # logic; this test is specifically about the DB-level FK).
        with db_engine.get_session() as session:
            session.execute(text(
                "DELETE FROM gemini.experiments WHERE id = :eid"
            ), {"eid": str(exp.id)})
            session.commit()

        with db_engine.get_session() as session:
            remaining = session.execute(text(
                "SELECT count(*) FROM gemini.jobs WHERE id = :id"
            ), {"id": str(job_id)}).scalar()
        assert remaining == 0, "job should have been cascade-deleted"

    def test_inserting_job_with_unknown_experiment_id_fails(self, setup_real_db):
        """The FK must reject inserts pointing at a non-existent
        experiment. Pre-0008 these inserts silently succeeded and
        produced the stranded rows we had to manually clean."""
        from gemini.db.core.base import db_engine
        from sqlalchemy.exc import IntegrityError

        bogus = uuid.uuid4()
        with db_engine.get_session() as session:
            with pytest.raises(IntegrityError):
                session.execute(text(
                    "INSERT INTO gemini.jobs (id, job_type, status, experiment_id) "
                    "VALUES (:id, 'RUN_ODM', 'PENDING', :eid)"
                ), {"id": str(uuid.uuid4()), "eid": str(bogus)})
                session.commit()


# ============================================================
# Fix 2: Experiment.delete() sweeps orphan-study sample accessions
# ============================================================

class TestExperimentDeleteCascadesStudySampleAccessions:

    def test_accession_reachable_only_via_orphan_study_samples_is_swept(
        self, setup_real_db,
    ):
        """The genomic ingest path creates accessions from .psam
        sample names. Pre-fix these were unreachable from the
        experiment cascade if no population was provided — the
        accession had no plot, no alias, no population link, only a
        genotyping_study_samples row pointing at the study. When the
        experiment was deleted, the cascade dropped the orphan study
        (cascading samples away via FK), but the accession survived
        with nothing pointing at it.
        """
        from gemini.db.core.base import db_engine
        from gemini.api.experiment import Experiment
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.genotyping_studies import GenotypingStudyModel
        from gemini.db.models.associations import (
            ExperimentGenotypingStudyModel,
        )
        from gemini.db.models.accessions import AccessionModel

        # Setup: experiment → study (linked via M2M) → sample → accession.
        exp = ExperimentModel.get_or_create(experiment_name="cascade-acc-exp")
        study = GenotypingStudyModel.get_or_create(study_name="cascade-acc-study")
        ExperimentGenotypingStudyModel.get_or_create(
            experiment_id=exp.id, study_id=study.id,
        )

        acc_id = uuid.uuid4()
        with db_engine.get_session() as session:
            session.execute(text(
                "INSERT INTO gemini.accessions (id, accession_name) "
                "VALUES (:id, :name)"
            ), {"id": str(acc_id), "name": "MAGIC-orphan-test"})
            # Sample row links study → accession. No population, no
            # plot, no alias — this is the only path from the
            # experiment to the accession.
            session.execute(text(
                "INSERT INTO gemini.genotyping_study_samples "
                "(study_id, accession_id, sample_index) "
                "VALUES (:sid, :aid, 0)"
            ), {"sid": str(study.id), "aid": str(acc_id)})
            session.commit()

        # Sanity: accession is alive before the cascade runs.
        assert AccessionModel.get(acc_id) is not None

        # Drop the experiment via the high-level cascade.
        exp_handle = Experiment.get_by_id(id=exp.id)
        assert exp_handle is not None
        ok = exp_handle.delete()
        assert ok, "Experiment.delete() should have succeeded"

        # The accession reachable only via the orphan study's sample
        # should have been swept.
        assert AccessionModel.get(acc_id) is None, (
            "MAGIC-orphan-test accession should have been swept by "
            "the experiment cascade — it was only reachable via the "
            "now-deleted orphan study's genotyping_study_samples row."
        )

    def test_accession_shared_with_surviving_study_is_kept(self, setup_real_db):
        """Mirror-image test: when an accession is also referenced by
        a study that survives the cascade (because that study is
        linked to a different experiment), the cascade must NOT
        delete it. Verifies the still_ref filter at the heart of the
        orphan sweep."""
        from gemini.db.core.base import db_engine
        from gemini.api.experiment import Experiment
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.genotyping_studies import GenotypingStudyModel
        from gemini.db.models.associations import (
            ExperimentGenotypingStudyModel,
        )
        from gemini.db.models.accessions import AccessionModel

        exp_to_drop = ExperimentModel.get_or_create(experiment_name="exp-to-drop")
        exp_to_keep = ExperimentModel.get_or_create(experiment_name="exp-to-keep")

        # Orphan study (linked only to exp_to_drop).
        orphan_study = GenotypingStudyModel.get_or_create(study_name="orphan-study")
        ExperimentGenotypingStudyModel.get_or_create(
            experiment_id=exp_to_drop.id, study_id=orphan_study.id,
        )
        # Shared study — linked to BOTH experiments; survives the drop.
        shared_study = GenotypingStudyModel.get_or_create(study_name="shared-study")
        ExperimentGenotypingStudyModel.get_or_create(
            experiment_id=exp_to_drop.id, study_id=shared_study.id,
        )
        ExperimentGenotypingStudyModel.get_or_create(
            experiment_id=exp_to_keep.id, study_id=shared_study.id,
        )

        # One accession reachable from BOTH studies' samples.
        acc_id = uuid.uuid4()
        with db_engine.get_session() as session:
            session.execute(text(
                "INSERT INTO gemini.accessions (id, accession_name) "
                "VALUES (:id, :name)"
            ), {"id": str(acc_id), "name": "MAGIC-shared-test"})
            session.execute(text(
                "INSERT INTO gemini.genotyping_study_samples "
                "(study_id, accession_id, sample_index) "
                "VALUES (:sid, :aid, 0)"
            ), {"sid": str(orphan_study.id), "aid": str(acc_id)})
            session.execute(text(
                "INSERT INTO gemini.genotyping_study_samples "
                "(study_id, accession_id, sample_index) "
                "VALUES (:sid, :aid, 0)"
            ), {"sid": str(shared_study.id), "aid": str(acc_id)})
            session.commit()

        # Drop exp_to_drop.
        handle = Experiment.get_by_id(id=exp_to_drop.id)
        assert handle is not None
        ok = handle.delete()
        assert ok

        # Accession should still be alive — the surviving shared study
        # still references it.
        assert AccessionModel.get(acc_id) is not None, (
            "Accession shared with a surviving study must be kept"
        )
