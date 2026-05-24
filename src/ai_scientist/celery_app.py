from __future__ import annotations

from .config import settings

try:
    from celery import Celery  # type: ignore

    celery_app = Celery("ai_scientist", broker=settings.redis_url, backend=settings.redis_url)
    celery_app.conf.beat_schedule = {
        "run-scheduled-agents-every-minute": {
            "task": "ai_scientist.celery_app.run_scheduled_agents",
            "schedule": 60.0,
        }
    }
except Exception:
    celery_app = None


if celery_app:

    @celery_app.task(name="ai_scientist.jobs.execute_job")
    def execute_job(job_payload: dict, payload: dict | None = None) -> dict:
        from .jobs import execute_job as run

        return run(job_payload, payload or {})

    @celery_app.task(name="ai_scientist.celery_app.run_scheduled_agents")
    def run_scheduled_agents() -> dict:
        from .autonomous import complete_literature_monitor, create_saved_search, literature_monitor_step
        from .jobs import queue_job
        from .store_factory import build_store

        store = build_store()
        checked = 0
        completed = 0
        for project in store.list_projects():
            for agent in project.autonomous_agents:
                if agent.status != "active" or agent.type != "literature_monitor":
                    continue
                checked += 1
                run = next(
                    (
                        item
                        for item in project.autonomous_agent_runs
                        if item.agent_id == agent.id and item.status in {"queued", "running"}
                    ),
                    None,
                )
                if not run:
                    continue
                search = project.saved_searches[0] if project.saved_searches else create_saved_search(project, agent.goal, agent.schedule or "weekly")
                literature_monitor_step(project, run, search.query)
                complete_literature_monitor(project, run, search)
                store.save_project(project)
                store.save_job(queue_job("agent_workflow", project.id, {"agent_id": agent.id, "run_id": run.id}))
                completed += 1
        return {"status": "scheduler_tick_completed", "checked": checked, "completed": completed}
