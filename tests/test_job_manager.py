"""Tests for API job manager."""

from pacs008.api.job_manager import JobManager, JobResult, JobStatus


class TestJobStatus:
    def test_enum_values(self):
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.SUCCESS == "success"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"


class TestJobResult:
    def test_creation(self):
        result = JobResult("test-id", JobStatus.PENDING)
        assert result.job_id == "test-id"
        assert result.status == JobStatus.PENDING
        assert result.result is None
        assert result.error is None
        assert result.progress_percent == 0

    def test_to_dict(self):
        result = JobResult("test-id", JobStatus.SUCCESS, result={"key": "val"})
        d = result.to_dict()
        assert d["job_id"] == "test-id"
        assert d["status"] == "success"
        assert d["result"] == {"key": "val"}
        assert "created_at" in d
        assert "updated_at" in d


class TestJobManager:
    def test_create_job(self):
        mgr = JobManager()
        job_id = mgr.create_job()
        assert job_id in mgr.jobs
        assert mgr.jobs[job_id].status == JobStatus.PENDING

    def test_get_job(self):
        mgr = JobManager()
        job_id = mgr.create_job()
        job = mgr.get_job(job_id)
        assert job is not None
        assert job.job_id == job_id

    def test_get_nonexistent_job(self):
        mgr = JobManager()
        assert mgr.get_job("nonexistent") is None

    def test_update_status(self):
        mgr = JobManager()
        job_id = mgr.create_job()
        mgr.update_status(job_id, JobStatus.PROCESSING, progress=50)
        job = mgr.get_job(job_id)
        assert job.status == JobStatus.PROCESSING
        assert job.progress_percent == 50

    def test_update_with_result(self):
        mgr = JobManager()
        job_id = mgr.create_job()
        mgr.update_status(
            job_id,
            JobStatus.SUCCESS,
            progress=100,
            result={"file": "out.xml"},
        )
        job = mgr.get_job(job_id)
        assert job.result == {"file": "out.xml"}

    def test_update_with_error(self):
        mgr = JobManager()
        job_id = mgr.create_job()
        mgr.update_status(job_id, JobStatus.FAILED, error="something broke")
        job = mgr.get_job(job_id)
        assert job.error == "something broke"

    def test_update_nonexistent_job(self):
        mgr = JobManager()
        mgr.update_status("nope", JobStatus.FAILED)  # Should not raise

    def test_cancel_job(self):
        mgr = JobManager()
        job_id = mgr.create_job()
        assert mgr.cancel_job(job_id)
        assert mgr.get_job(job_id).status == JobStatus.CANCELLED

    def test_cancel_completed_job(self):
        mgr = JobManager()
        job_id = mgr.create_job()
        mgr.update_status(job_id, JobStatus.SUCCESS)
        assert not mgr.cancel_job(job_id)  # Can't cancel completed

    def test_cancel_nonexistent_job(self):
        mgr = JobManager()
        assert not mgr.cancel_job("nonexistent")

    def test_cleanup_old_jobs(self):
        mgr = JobManager()
        # Create many completed jobs
        for _ in range(10):
            job_id = mgr.create_job()
            mgr.update_status(job_id, JobStatus.SUCCESS)

        assert len(mgr.jobs) == 10
        mgr.cleanup_old_jobs(keep_count=3)
        assert len(mgr.jobs) == 3

    def test_cleanup_keeps_pending(self):
        mgr = JobManager()
        pending_id = mgr.create_job()
        for _ in range(5):
            jid = mgr.create_job()
            mgr.update_status(jid, JobStatus.SUCCESS)

        mgr.cleanup_old_jobs(keep_count=2)
        # Pending job should remain + 2 completed
        assert pending_id in mgr.jobs

    def test_progress_clamped(self):
        mgr = JobManager()
        job_id = mgr.create_job()
        mgr.update_status(job_id, JobStatus.PROCESSING, progress=150)
        assert mgr.get_job(job_id).progress_percent == 100
        mgr.update_status(job_id, JobStatus.PROCESSING, progress=-10)
        assert mgr.get_job(job_id).progress_percent == 0
