# file: src/crew/crew.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


def _ensure_dir(path: str | Path) -> None:
    p = Path(path)
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)


def _get(cfg: Dict[str, Any], key: str, kind: str) -> Dict[str, Any]:
    # Why: explicit, early error if YAML key is missing.
    if key not in cfg or not isinstance(cfg[key], dict):
        raise KeyError(f"Missing {kind} config for '{key}'. Check your YAML.")
    return cfg[key]


@CrewBase
class WebsiteCreator:
    """WebsiteCreator crew"""

    # CrewBase will load these YAMLs into dicts on self.agents_config / self.tasks_config
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self) -> None:
        # Ensure artifacts dir exists before any Task tries to write.
        _ensure_dir("artifacts")

    # ---------------------------
    # Agents
    # ---------------------------

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=_get(self.agents_config, "planner", "agent"),  # type: ignore[arg-type]
            verbose=True,
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=180,
            max_retry_limit=2,
            callbacks=[],
            tags=["planner", "requirements"],
            seed=7,
        )

    @agent
    def team_leader(self) -> Agent:
        return Agent(
            config=_get(self.agents_config, "team_leader", "agent"),
            verbose=True,
            allow_delegation=True,
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=240,
            max_retry_limit=2,
            callbacks=[],
            tags=["leader", "router"],
            seed=7,
        )

    @agent
    def frontend_developer(self) -> Agent:
        return Agent(
            config=_get(self.agents_config, "frontend_developer", "agent"),
            verbose=True,
            allow_code_execution=True,  # only if you actually use code-exec tools
            code_execution_mode="safe",
            max_execution_time=600,
            max_retry_limit=3,
            callbacks=[],
            tags=["frontend", "ui", "gradio"],
            seed=7,
        )

    @agent
    def backend_developer(self) -> Agent:
        return Agent(
            config=_get(self.agents_config, "backend_developer", "agent"),
            verbose=True,
            allow_code_execution=True,
            code_execution_mode="safe",
            max_execution_time=600,
            max_retry_limit=3,
            callbacks=[],
            tags=["backend", "api", "db"],
            seed=7,
        )

    @agent
    def integrator(self) -> Agent:
        return Agent(
            config=_get(self.agents_config, "integrator", "agent"),
            verbose=True,
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=300,
            max_retry_limit=2,
            callbacks=[],
            tags=["integrator", "devops", "merge"],
            seed=7,
        )

    @agent
    def tester(self) -> Agent:
        return Agent(
            config=_get(self.agents_config, "tester", "agent"),
            verbose=True,
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=180,
            max_retry_limit=2,
            callbacks=[],
            tags=["qa", "tester", "e2e"],
            seed=7,
        )

    @agent
    def evaluator(self) -> Agent:
        return Agent(
            config=_get(self.agents_config, "evaluator", "agent"),
            verbose=True,
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=180,
            max_retry_limit=2,
            callbacks=[],
            tags=["evaluator", "review", "quality"],
            seed=7,
        )

    @agent
    def repository_manager(self) -> Agent:
        return Agent(
            config=_get(self.agents_config, "repository_manager", "agent"),
            verbose=True,
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=300,
            max_retry_limit=2,
            callbacks=[],
            tags=["repo", "consistency", "packaging"],
            seed=7,
        )

    # ---------------------------
    # Tasks
    # ---------------------------

    @task
    def planner_task(self) -> Task:
        # NOTE: enforce_json_schema=True only if your tasks.yaml defines expected_output_schema
        return Task(
            config=_get(self.tasks_config, "planner_task", "task"),
            verbose=True,
            output_file="artifacts/planner.json",
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=180,
            max_retry_limit=2,
            enforce_json_schema=True,
            retry_on_schema_fail=True,
            callbacks=[],
            context={"customer_request": "{customer_request}"},
        )

    @task
    def team_leader_task(self) -> Task:
        return Task(
            config=_get(self.tasks_config, "team_leader_task", "task"),
            verbose=True,
            output_file="artifacts/blueprint.md",
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=180,
            max_retry_limit=2,
            enforce_json_schema=False,  # blueprint can be Markdown
            retry_on_schema_fail=False,
            callbacks=[],
            context={
                "planner_output": "planner_task.output",
                "website_name": "{website_name}",
            },
        )

    @task
    def frontend_developer_task(self) -> Task:
        return Task(
            config=_get(self.tasks_config, "frontend_developer_task", "task"),
            verbose=True,
            output_file="artifacts/frontend.json",
            allow_code_execution=True,
            code_execution_mode="safe",
            max_execution_time=600,
            max_retry_limit=3,
            enforce_json_schema=True,
            retry_on_schema_fail=True,
            callbacks=[],
            context={
                "planner_output": "planner_task.output",
                "leader_blueprint": "team_leader_task.output",
                "ui_framework": "gradio",
            },
        )

    @task
    def backend_developer_task(self) -> Task:
        return Task(
            config=_get(self.tasks_config, "backend_developer_task", "task"),
            verbose=True,
            output_file="artifacts/backend.json",
            allow_code_execution=True,
            code_execution_mode="safe",
            max_execution_time=600,
            max_retry_limit=3,
            enforce_json_schema=True,
            retry_on_schema_fail=True,
            callbacks=[],
            context={
                "planner_output": "planner_task.output",
                "leader_blueprint": "team_leader_task.output",
                "shared_classes": "frontend_developer_task.output.shared_classes",
            },
        )

    @task
    def integration_task(self) -> Task:
        return Task(
            config=_get(self.tasks_config, "integration_task", "task"),
            verbose=True,
            output_file="artifacts/integration.json",
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=360,
            max_retry_limit=2,
            enforce_json_schema=True,
            retry_on_schema_fail=True,
            callbacks=[],
            context={
                "frontend_artifact": "frontend_developer_task.output",
                "backend_artifact": "backend_developer_task.output",
                "planner_output": "planner_task.output",
            },
        )

    @task
    def repository_management_task(self) -> Task:
        return Task(
            config=_get(self.tasks_config, "repository_management_task", "task"),
            verbose=True,
            output_file="artifacts/repository.json",
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=240,
            max_retry_limit=2,
            enforce_json_schema=True,
            retry_on_schema_fail=True,
            callbacks=[],
            context={
                "integration_output": "integration_task.output",
                "website_folder": "website",
            },
        )

    @task
    def testing_task(self) -> Task:
        return Task(
            config=_get(self.tasks_config, "testing_task", "task"),
            verbose=True,
            output_file="artifacts/test_report.json",
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=300,
            max_retry_limit=2,
            enforce_json_schema=True,
            retry_on_schema_fail=True,
            callbacks=[],
            context={
                "features": "planner_task.output.features",
                "final_directory": "repository_management_task.output.final_directory",
                "launch_cmd": "python app.py",
            },
        )

    @task
    def evaluation_task(self) -> Task:
        return Task(
            config=_get(self.tasks_config, "evaluation_task", "task"),
            verbose=True,
            output_file="artifacts/evaluation.json",
            allow_code_execution=False,
            code_execution_mode="safe",
            max_execution_time=180,
            max_retry_limit=2,
            enforce_json_schema=True,
            retry_on_schema_fail=True,
            callbacks=[],
            context={
                "customer_request": "{customer_request}",
                "test_report": "testing_task.output",
                "repo_summary": "repository_management_task.output",
            },
        )

    # ---------------------------
    # Crew
    # ---------------------------

    @crew(
        agents=[
            "planner",
            "team_leader",
            "frontend_developer",
            "backend_developer",
            "integrator",
            "repository_manager",
            "tester",
            "evaluator",
        ],
        tasks=[
            "planner_task",
            "team_leader_task",
            "frontend_developer_task",
            "backend_developer_task",
            "integration_task",
            "repository_management_task",
            "testing_task",
            "evaluation_task",
        ],
    )
    def crew(self) -> Crew:
        """Creates the hierarchical crew with a manager (team_leader)."""
        # IMPORTANT: manager_agent must be an Agent instance, not a function.
        manager = self.agents["team_leader"]  # provided by CrewBase registry
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=True,
        )

    # Optional convenience runner
    def run(self, customer_request: str, website_name: str | None = None) -> Dict[str, Any]:
        inputs = {
            "customer_request": customer_request,
            "website_name": website_name or "Generated Website",
        }
        return self.crew().kickoff(inputs=inputs)
