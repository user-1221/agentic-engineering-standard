"""Domain-specific configuration for aes init.

Each supported domain (ml, web, devops) has pre-filled content drawn from
the reference examples.  Templates receive a DomainConfig instance; when it
is None the templates fall back to the existing TODO scaffolding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillDef:
    """Definition for a single skill (manifest + runbook content)."""

    id: str
    name: str
    version: str
    description: str
    stage: int
    phase: str
    inputs_required: List[Dict[str, str]] = field(default_factory=list)
    inputs_optional: List[Dict[str, str]] = field(default_factory=list)
    inputs_environment: List[str] = field(default_factory=list)
    outputs: List[Dict[str, str]] = field(default_factory=list)
    trigger_command: str = ""
    error_strategy: str = "per-item-isolation"
    code_primary: str = ""
    tags: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    # New fields: description quality, activation, permissions
    negative_triggers: List[str] = field(default_factory=list)
    activation: str = "explicit"  # "auto", "explicit", or "hybrid"
    allowed_tools: Optional[Dict[str, object]] = None
    # OpenClaw-specific fields
    emoji: str = ""
    requires_bins: List[str] = field(default_factory=list)
    requires_env: List[str] = field(default_factory=list)
    primary_env: str = ""
    user_invocable: bool = True
    license_id: str = "MIT"
    mcp_server: Optional[Dict[str, object]] = None
    # Runbook content sections
    runbook_purpose: str = ""
    runbook_when: str = ""
    runbook_how: str = ""
    runbook_decision_tree: str = ""
    runbook_error_handling: str = ""


@dataclass
class WorkflowStateDef:
    """A single state in a workflow."""

    id: str
    description: str
    initial: bool = False
    terminal: bool = False
    active: bool = False


@dataclass
class WorkflowTransitionDef:
    """A transition between workflow states."""

    from_state: str
    to_state: str
    skill: str = ""
    conditions: List[str] = field(default_factory=list)
    on_failure: str = ""
    description: str = ""


@dataclass
class WorkflowDef:
    """Complete workflow definition."""

    id: str
    entity: str
    description: str
    states: List[WorkflowStateDef] = field(default_factory=list)
    transitions: List[WorkflowTransitionDef] = field(default_factory=list)


@dataclass
class CommandDef:
    """Definition for a workflow-initiating command (e.g. /train, /build)."""

    id: str
    trigger: str              # e.g. "/build", "/train", "/process"
    description: str
    runbook_purpose: str
    runbook_phases: List[Dict[str, str]] = field(default_factory=list)
    worker_specialty: str = ""  # one-line specialty for worker identity in memory


@dataclass
class DomainConfig:
    """All domain-specific content for aes init."""

    mode: str = "dev-assist"   # "dev-assist" or "agent-integrated"
    workflow_commands: List[CommandDef] = field(default_factory=list)

    # instructions.md content
    instructions_description: str = ""
    instructions_quick_ref: str = ""
    instructions_project_structure: str = ""
    instructions_rules: List[str] = field(default_factory=list)
    instructions_workflow_phases: List[Dict[str, str]] = field(default_factory=list)
    instructions_key_principle: str = ""
    instructions_gotchas: List[str] = field(default_factory=list)

    # Skills
    skills: List[SkillDef] = field(default_factory=list)

    # Orchestrator content
    orchestrator_pipeline: str = ""
    orchestrator_status_flow: str = ""
    orchestrator_decision_tree: str = ""
    orchestrator_when_to_stop: str = ""

    # Workflow
    workflow: Optional[WorkflowDef] = None

    # Permissions additions
    permissions_shell_read: List[str] = field(default_factory=list)
    permissions_shell_execute: List[str] = field(default_factory=list)
    permissions_file_write: List[str] = field(default_factory=list)
    permissions_deny_shell: List[str] = field(default_factory=list)
    permissions_confirm_shell: List[str] = field(default_factory=list)
    permissions_confirm_actions: List[str] = field(default_factory=list)
    permissions_resource_limits: Optional[Dict[str, object]] = None

    # Environment
    env_required: List[Dict[str, str]] = field(default_factory=list)
    env_optional: List[Dict[str, str]] = field(default_factory=list)

    # OpenClaw / daemon-agent fields
    identity_persona: str = ""
    identity_name: str = ""
    identity_emoji: str = ""
    model_provider: str = ""
    model_model: str = ""
    sandbox_enabled: bool = False
    sandbox_runtime: str = "docker"
    heartbeat_interval: int = 30
    heartbeat_checklist: str = ""
    channels: Dict[str, Dict[str, str]] = field(default_factory=dict)

    # Lifecycle / Learning / Rules scaffolding
    scaffold_lifecycle: bool = True
    scaffold_learning: bool = False   # True for agent-integrated domains
    scaffold_rules: bool = True
    lifecycle_profile: str = "standard"


# ---------------------------------------------------------------------------
# ML domain config — drawn from examples/ml-pipeline
# ---------------------------------------------------------------------------

_ML_SKILLS = [
    SkillDef(
        id="discover",
        name="Discover Datasets",
        version="1.0.0",
        description="Find new public datasets from OpenML and Kaggle APIs. Use when the pipeline needs fresh data or no datasets are in discovered status. Queries multiple sources, deduplicates, and filters by quality criteria.",
        stage=1,
        phase="ingestion",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "Active database connection"},
        ],
        inputs_optional=[
            {"name": "max_datasets", "type": "int", "default": "50",
             "description": "Maximum datasets to discover per run"},
        ],
        inputs_environment=["OPENML_APIKEY", "KAGGLE_USERNAME", "KAGGLE_KEY"],
        outputs=[
            {"name": "new_dataset_ids", "type": "list[int]",
             "description": "IDs of newly discovered datasets"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage discover",
        error_strategy="per-item-isolation",
        code_primary="pipeline/discover.py",
        tags=["data-ingestion", "openml", "kaggle"],
        blocks=["examine"],
        negative_triggers=["Do NOT use for manual CSV imports or local file ingestion"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "data/**"]}, "network": True},
        runbook_purpose="Find new public datasets from OpenML and Kaggle that meet quality and licensing criteria.",
        runbook_when="- No datasets in `discovered` status\n- User requests new data sources\n- Scheduled daily",
        runbook_how="1. Query OpenML API for datasets matching size/license filters\n2. Query Kaggle API for datasets in target domains\n3. Deduplicate against existing records via `dataset_exists()`\n4. Insert new records via `insert_dataset()`\n5. Record attribution via `insert_attribution()`",
        runbook_decision_tree="For each candidate dataset:\n  |- Already exists? -> Skip\n  |- License not in whitelist? -> Skip\n  |- Rows < 100 or > 500,000? -> Skip\n  |- Features < 3? -> Skip\n  \\- Passes all checks? -> Insert as \"discovered\"",
        runbook_error_handling="- **API timeout**: Retry once, then skip source\n- **Rate limit**: Sleep and retry\n- **Invalid response**: Log debug, skip dataset",
    ),
    SkillDef(
        id="examine",
        name="Examine Dataset",
        version="1.0.0",
        description="Download, profile, and compute quality score for a dataset. Use after discover completes and datasets are in discovered status. Detects feature types, checks hard rejections, and saves as parquet.",
        stage=2,
        phase="profiling",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "Active database connection"},
            {"name": "dataset_id", "type": "int",
             "description": "Dataset to examine"},
        ],
        outputs=[
            {"name": "quality_score", "type": "float",
             "description": "0.0-1.0 weighted quality score"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage examine --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/examine.py",
        tags=["data-quality", "profiling"],
        depends_on=["discover"],
        negative_triggers=["Do NOT use on datasets already at examined status or beyond"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "data/**"]}, "network": True},
        runbook_purpose="Download a dataset, compute quality score, detect feature types, and decide if it's worth training on.",
        runbook_when="- Dataset is at `discovered` status\n- After discover skill completes",
        runbook_how="1. Download data from source (OpenML API or Kaggle)\n2. Compute quality score (weighted): missing 30%, dupes 15%, constants 15%, imbalance 20%, features 10%, cardinality 10%\n3. Check hard rejections: >50% missing, <3 features, <10 minority samples\n4. Detect feature types: numeric, categorical, datetime, text\n5. Save as parquet\n6. Advance to `examined`",
        runbook_decision_tree="Download dataset\n  |- Download fails? -> Reject: \"download_failed\"\n  |- >50% missing values? -> Reject: \"too_many_missing\"\n  |- <3 features? -> Reject: \"too_few_features\"\n  |- <10 minority samples? -> Reject: \"insufficient_minority\"\n  \\- Passes? -> Status: \"examined\"",
        runbook_error_handling="- **Network error**: Log and continue\n- **Invalid data**: Skip with log",
    ),
    SkillDef(
        id="classify",
        name="Classify Problem",
        version="1.0.0",
        description="Detect problem type and select candidate models from the registry. Use after examine when datasets reach examined status with quality_score >= 0.30. Supports binary, multiclass, regression, time-series, anomaly, and clustering.",
        stage=3,
        phase="classification",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "Active database connection"},
            {"name": "dataset_id", "type": "int",
             "description": "Dataset to classify"},
        ],
        outputs=[
            {"name": "problem_type", "type": "str",
             "description": "Detected problem type (binary, multiclass, regression, etc.)"},
            {"name": "selected_models", "type": "list[str]",
             "description": "Model keys selected from the registry"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage classify --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/classify.py",
        tags=["classification", "model-selection"],
        depends_on=["examine"],
        blocks=["train"],
        negative_triggers=["Do NOT use on datasets below quality threshold (quality_score < 0.30)"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**"]}, "network": False},
        runbook_purpose="Detect the problem type (binary, multiclass, regression, time-series, anomaly, clustering) and select candidate models from the model registry.",
        runbook_when="- Dataset is at `examined` status\n- After examine skill completes with quality_score >= 0.30",
        runbook_how="1. Load dataset profile from examine stage\n2. Analyze target column: cardinality, distribution, dtype\n3. Detect problem type using heuristics\n4. Query model_registry for compatible models\n5. Filter models by dataset size and feature types\n6. Save selected models and advance to `classified`",
        runbook_decision_tree="Analyze target column:\n  |- Numeric + high cardinality? -> regression\n  |- Categorical + 2 classes? -> binary_classification\n  |- Categorical + 3+ classes? -> multiclass_classification\n  |- Datetime target? -> time_series\n  |- No target column? -> clustering or anomaly_detection\n  \\- Ambiguous? -> Default to multiclass_classification\n\nFor each compatible model:\n  |- Supports problem type? -> Include\n  \\- Not compatible? -> Skip",
        runbook_error_handling="- **Ambiguous target**: Default to multiclass, log warning\n- **No compatible models**: Reject dataset with reason",
    ),
    SkillDef(
        id="train",
        name="Train Models",
        version="1.0.0",
        description="Run Optuna HPO and train all candidate models for a dataset. Use after classify when datasets reach classified status and resource limits are met. Trains each model independently with per-item isolation.",
        stage=4,
        phase="training",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "Active database connection"},
            {"name": "dataset_id", "type": "int",
             "description": "Dataset to train"},
        ],
        inputs_optional=[
            {"name": "model_keys", "type": "list[str]",
             "description": "Specific models to train (default: all selected)"},
        ],
        inputs_environment=["OPTUNA_TIMEOUT", "OPTUNA_N_TRIALS"],
        outputs=[
            {"name": "experiment_ids", "type": "list[int]",
             "description": "IDs of completed experiments"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage train --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/train.py",
        tags=["training", "optuna", "hpo"],
        depends_on=["classify"],
        blocks=["evaluate"],
        negative_triggers=["Do NOT use when CPU > 70% or memory > 75%", "Do NOT use on unclassified datasets"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "models/**", "data/**"]}, "network": False},
        runbook_purpose="Run Optuna hyperparameter optimization and train all candidate models for a dataset.",
        runbook_when="- Dataset is at `classified` status\n- Resource limits met (CPU <70%, memory <75%)",
        runbook_how="For each selected model:\n1. Preprocess data (framework-aware)\n2. Run Optuna HPO (TPESampler, MedianPruner)\n3. Train final model on best params\n4. Evaluate on held-out test set\n5. Save model in native format\n6. Log to MLflow and SQLite",
        runbook_decision_tree="For each model_key in selected_models:\n  |- Preprocess fails? -> Mark experiment failed, continue\n  |- Optuna finds no good trial? -> Mark failed, continue\n  |- Training crashes? -> Mark failed with error_message, continue\n  \\- Success? -> Save model, log metrics, mark completed\n\nAfter all models:\n  |- At least 1 completed? -> Status: \"trained\"\n  \\- All failed? -> Status: \"rejected\"",
        runbook_error_handling="- Each model trains independently (per-item-isolation)\n- One model failing doesn't affect others\n- Error messages stored in experiment.error_message",
    ),
    SkillDef(
        id="evaluate",
        name="Evaluate Models",
        version="1.0.0",
        description="Compare trained models, check overfitting, and apply quality gates. Use after train when datasets reach trained status with at least one completed experiment. Ranks models, detects overfitting, and validates against baselines.",
        stage=5,
        phase="evaluation",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "Active database connection"},
            {"name": "dataset_id", "type": "int",
             "description": "Dataset to evaluate"},
        ],
        inputs_optional=[
            {"name": "quality_gates", "type": "dict",
             "description": "Custom quality gate thresholds (default: from config)"},
        ],
        outputs=[
            {"name": "best_experiment_id", "type": "int",
             "description": "ID of the best performing experiment"},
            {"name": "passes_quality_gates", "type": "bool",
             "description": "Whether the best model meets quality criteria"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage evaluate --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/evaluate.py",
        tags=["evaluation", "quality-gates", "model-comparison"],
        depends_on=["train"],
        blocks=["package"],
        negative_triggers=["Do NOT use when no experiments have completed"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**"]}, "network": False},
        runbook_purpose="Compare all trained models, detect overfitting, check quality gates, and select the best experiment.",
        runbook_when="- Dataset is at `trained` status\n- At least one experiment completed successfully",
        runbook_how="1. Load all completed experiments for the dataset\n2. Rank by primary metric (accuracy, RMSE, etc.)\n3. Check overfitting: train-val gap > 0.15 is a warning\n4. Check quality gates: minimum metric thresholds\n5. Check baseline: best model must beat random/majority\n6. Select best experiment and advance to `evaluated`",
        runbook_decision_tree="For each completed experiment:\n  |- Train-val gap > 0.15? -> Flag overfitting warning\n  |- Below quality gate? -> Mark as not passing\n  |- Worse than baseline? -> Mark as not passing\n  \\- Passes all checks? -> Candidate for best\n\nAfter ranking:\n  |- At least 1 passes? -> Select best, status: ready for packaging\n  \\- None pass? -> Consider reframe (back to classify)",
        runbook_error_handling="- **No experiments**: Cannot evaluate, keep at trained status\n- **All overfitting**: Log warning, still select best if above quality gate",
    ),
    SkillDef(
        id="package",
        name="Package Model",
        version="1.0.0",
        description="Export best model in native format and create deployment zip bundle. Use after evaluate confirms passes_quality_gates=true. Supports CatBoost, XGBoost, LightGBM, and sklearn serialization formats.",
        stage=6,
        phase="packaging",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "Active database connection"},
            {"name": "dataset_id", "type": "int",
             "description": "Dataset whose best model to package"},
        ],
        outputs=[
            {"name": "package_path", "type": "str",
             "description": "Path to the created zip bundle"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage package --dataset-id {ID}",
        error_strategy="fail-fast",
        code_primary="pipeline/package.py",
        tags=["packaging", "serialization", "deployment"],
        depends_on=["evaluate"],
        blocks=["publish"],
        negative_triggers=["Do NOT use when best model fails quality gates"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "models/**", "packages/**"]}, "network": False},
        runbook_purpose="Export the best model in its native serialization format and bundle it into a deployment-ready zip.",
        runbook_when="- Dataset has a best experiment that passes quality gates\n- After evaluate skill confirms passes_quality_gates=true",
        runbook_how="1. Load best experiment and its trained model\n2. Export in native format (CatBoost .cbm, XGBoost .json, LightGBM .txt, sklearn .joblib)\n3. Generate model card with metrics and metadata\n4. Create zip bundle: model file + model card + config\n5. Verify bundle integrity\n6. Advance to `packaged`",
        runbook_decision_tree="Load best experiment:\n  |- Model file exists? -> Export in native format\n  |   |- CatBoost? -> .cbm format\n  |   |- XGBoost? -> .json format\n  |   |- LightGBM? -> .txt format\n  |   \\- sklearn? -> .joblib format\n  |- Model file missing? -> Abort, re-train needed\n  \\- Bundle created? -> Verify checksum, advance status",
        runbook_error_handling="- **Model file missing**: Abort, dataset stays at trained\n- **Serialization error**: Log error, try alternative format\n- **Zip creation failure**: Retry once, then abort",
    ),
    SkillDef(
        id="publish",
        name="Publish Model",
        version="1.0.0",
        description="Upload model to HuggingFace Hub and register with the prediction API. Use after package when a verified zip bundle exists. Requires HF_TOKEN environment variable.",
        stage=7,
        phase="distribution",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "Active database connection"},
            {"name": "dataset_id", "type": "int",
             "description": "Dataset whose packaged model to publish"},
        ],
        inputs_environment=["HF_TOKEN"],
        outputs=[
            {"name": "published_urls", "type": "list[str]",
             "description": "URLs where the model is now available"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage publish --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/publish.py",
        tags=["publishing", "huggingface", "api-registration"],
        depends_on=["package"],
        negative_triggers=["Do NOT use without HF_TOKEN configured", "Do NOT use on unpackaged models"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**"]}, "network": True},
        runbook_purpose="Upload the packaged model to HuggingFace Hub and register it with the metered prediction API.",
        runbook_when="- Dataset is at `packaged` status\n- Package zip exists and is verified\n- HF_TOKEN environment variable is set",
        runbook_how="1. Load package zip from package stage\n2. Upload to HuggingFace Hub with model card\n3. Register model with prediction API endpoint\n4. Generate API key for metered access\n5. Verify both platforms respond correctly\n6. Advance to `published`",
        runbook_decision_tree="Publish to platforms:\n  |- HuggingFace upload\n  |   |- Success? -> Record URL\n  |   \\- Failure? -> Log error, continue to API\n  |- API registration\n  |   |- Success? -> Record endpoint URL\n  |   \\- Failure? -> Log error\n  \\- At least one succeeded? -> Status: published\n     \\- Both failed? -> Keep at packaged, log errors",
        runbook_error_handling="- **HF_TOKEN invalid**: Abort HF upload, try API only\n- **Network error**: Retry once per platform\n- **API registration failure**: Log and keep at packaged status",
    ),
]

_ML_WORKFLOW = WorkflowDef(
    id="dataset-pipeline",
    entity="dataset",
    description="Dataset lifecycle from discovery through publication",
    states=[
        WorkflowStateDef("discovered", "Found and registered in database", initial=True),
        WorkflowStateDef("examined", "Downloaded, profiled, quality-scored"),
        WorkflowStateDef("classified", "Problem type detected, models selected"),
        WorkflowStateDef("training", "Models being trained", active=True),
        WorkflowStateDef("trained", "All models trained, awaiting evaluation"),
        WorkflowStateDef("packaged", "Best model packaged as zip"),
        WorkflowStateDef("published", "Live on API and HuggingFace", terminal=True),
        WorkflowStateDef("rejected", "Failed quality criteria", terminal=True),
    ],
    transitions=[
        WorkflowTransitionDef("discovered", "examined", skill="examine",
                              conditions=["Data file downloadable"], on_failure="rejected"),
        WorkflowTransitionDef("examined", "classified", skill="classify",
                              conditions=["quality_score >= 0.30"], on_failure="rejected"),
        WorkflowTransitionDef("classified", "training", skill="train",
                              conditions=["At least one model selected", "Resource limits met"]),
        WorkflowTransitionDef("training", "trained", skill="train",
                              conditions=["At least one experiment completed"],
                              on_failure="rejected"),
        WorkflowTransitionDef("trained", "packaged", skill="package",
                              conditions=["Best experiment passes quality gates",
                                          "Best experiment beats baseline"],
                              on_failure="rejected"),
        WorkflowTransitionDef("packaged", "published", skill="publish",
                              conditions=["At least one platform succeeds"]),
        WorkflowTransitionDef("trained", "classified", skill="classify",
                              conditions=["All models below quality gates"],
                              description="Reframe problem type when all models fail"),
    ],
)

ML_CONFIG = DomainConfig(
    mode="agent-integrated",
    workflow_commands=[
        CommandDef(
            id="build",
            trigger="/build",
            description="Build the ML pipeline codebase from scratch: project structure, database, pipeline stages, model registry, config, scripts, tests",
            runbook_purpose="Construct the complete ML pipeline codebase. The agent creates project structure, sets up the database, implements each pipeline stage, builds the model registry, writes configuration, adds CLI scripts, and verifies with tests.",
            worker_specialty="Constructing ML pipeline codebases — modules, database, stages, registry",
            runbook_phases=[
                {"title": "Project Structure", "content": "Create directory layout: pipeline/, trainers/, config/, serving/, scripts/, tests/. Set up pyproject.toml, __init__.py files, and virtual environment."},
                {"title": "Database & Storage", "content": "Implement SQLite schema for datasets, models, and runs. Create migration scripts and helper functions (insert, update, query)."},
                {"title": "Pipeline Stages", "content": "Build each stage module: discover.py, examine.py, classify.py, train.py, evaluate.py, package.py, publish.py. Each reads from DB, processes, writes results back."},
                {"title": "Model Registry", "content": "Create config/model_registry.py — the brain. Define model entries (name, class, search space, metrics). Adding a model = adding a dict entry."},
                {"title": "Configuration", "content": "Create config/settings.py with environment-based config. Define quality gates, thresholds, resource limits, and API endpoints."},
                {"title": "Scripts & CLI", "content": "Build scripts/run_pipeline.py with --stage and --dataset-id flags. Add convenience scripts for common operations."},
                {"title": "Tests & Verification", "content": "Write unit tests for each pipeline stage. Add integration test that runs discover->examine->classify on a small dataset. Verify all imports and CLI commands work."},
            ],
        ),
        CommandDef(
            id="train",
            trigger="/train",
            description="Run the full ML pipeline: discover, examine, classify, train, evaluate, package, publish",
            runbook_purpose="Execute the complete ML pipeline end-to-end. The agent discovers datasets, profiles them, trains models via Optuna HPO, evaluates results, and publishes winners.",
            worker_specialty="Executing ML training pipelines — HPO, evaluation, packaging",
            runbook_phases=[
                {"title": "Discover", "content": "Find new datasets from OpenML/Kaggle APIs matching quality and licensing criteria."},
                {"title": "Examine", "content": "Download, profile, and compute quality scores. Reject datasets below thresholds."},
                {"title": "Classify", "content": "Detect problem type and select candidate models from the registry."},
                {"title": "Train", "content": "Run Optuna HPO for each candidate model. Train final models on best params."},
                {"title": "Evaluate", "content": "Score models against quality gates. Compare to baselines."},
                {"title": "Package", "content": "Serialize models, generate model cards, and prepare artifacts."},
                {"title": "Publish", "content": "Push passing models to HuggingFace Hub with full metadata."},
            ],
        ),
    ],
    instructions_description="Automated ML pipeline that discovers datasets, trains models, evaluates quality, packages winners, and serves predictions.",
    instructions_quick_ref="<!-- AGENT: Extract commands from scripts/, Makefile, or pyproject.toml. Show the 3-5 most common commands for running the pipeline, training, and testing. -->",
    instructions_project_structure="<!-- AGENT: Run directory listing and annotate key directories. Typical ML pipeline structure: pipeline stages, model trainers, configuration, serving layer, scripts, tests. -->",
    instructions_rules=[
        "**Model registry is the brain** -- adding a model means adding a configuration entry, not writing new training code.",
        "**Resource limits** -- monitor CPU and memory during training. Skip or queue work when limits are exceeded.",
        "**Fail graceful** -- each dataset/model wrapped in error handling. Log the error, continue with the next item.",
    ],
    instructions_workflow_phases=[
        {"title": "Find Data", "content": "Search data sources or ingest user-provided datasets."},
        {"title": "Run Pipeline", "content": "Execute discover -> examine -> classify -> train -> evaluate stages."},
        {"title": "Analyze Results (DO NOT SKIP)", "content": "Check for: overfitting (train-val gap too large), underfitting (below quality gates), all models failed, baseline not beaten, problem type mismatch."},
        {"title": "Iterate", "content": "Levers in order: hyperparameter tuning (more trials/time) -> model selection (search space) -> problem reframing -> preprocessing changes -> quality gate adjustment."},
        {"title": "Package and Publish", "content": "Only after quality is confirmed. Evaluate -> package -> publish."},
    ],
    instructions_key_principle="The agent's job is NOT just to run commands. It is to understand, analyze, iterate, and deliver quality.",
    instructions_gotchas=[],
    skills=_ML_SKILLS,
    orchestrator_pipeline="discover -> examine -> classify -> train -> evaluate -> package -> publish",
    orchestrator_status_flow="discovered -> examined -> classified -> training -> trained -> packaged -> published\n    |            |                                 |\n    v            v                                 v\n rejected     rejected                          rejected",
    orchestrator_decision_tree="FIRST: Check if pipeline is already complete (all items at terminal status).\n  If complete -> report status summary, ask user: re-run / new session / re-validate / exit.\n  If not -> proceed:\n\nfor each stage in [discover, examine, classify, train, evaluate, package, publish]:\n  1. Check resource limits (CPU <70%, memory <75%)\n  2. Get datasets at current status (or single dataset if --dataset-id)\n  3. For each dataset:\n     a. Run stage function\n     b. On success: advance status to next stage\n     c. On failure: log error, mark rejected if unrecoverable\n  4. Report: N processed, N failed, N skipped\n\nSpecial: after train stage, run ANALYSIS before evaluate:\n  - Check overfitting (train-val gap >0.15)\n  - Check underfitting (all below quality gates)\n  - Check baseline (better than random?)\n  - If all fail: consider reframe (trained -> classified)",
    orchestrator_when_to_stop="- All datasets at terminal status (published or rejected)\n- Resource limits exceeded\n- User requests stop\n- No datasets to process",
    workflow=_ML_WORKFLOW,
    permissions_shell_read=[
        "scripts/job.sh status *",
        "scripts/job.sh logs *",
        "scripts/job.sh list",
        "scripts/job.sh results *",
    ],
    permissions_shell_execute=[
        "python scripts/run_pipeline.py *",
        "python -m pytest *",
        "scripts/job.sh start *",
    ],
    permissions_file_write=[
        "config/**/*.py",
        "pipeline/**/*.py",
        "trainers/**/*.py",
    ],
    permissions_deny_shell=[
        "rm -rf *",
        "docker rm *",
        "systemctl *",
        "kill *",
    ],
    permissions_confirm_shell=[
        "scripts/job.sh stop *",
        "git push *",
    ],
    permissions_confirm_actions=["publish_model", "create_api_key", "lower_quality_gates"],
    permissions_resource_limits={
        "max_cpu_percent": 70,
        "max_memory_percent": 75,
        "check_before": ["train", "evaluate"],
        "on_exceeded": "warn_and_skip",
    },
    env_required=[
        {"name": "OPENML_APIKEY", "description": "OpenML API key for dataset discovery"},
        {"name": "HF_TOKEN", "description": "HuggingFace token for model publishing"},
    ],
    env_optional=[
        {"name": "OPTUNA_TIMEOUT", "default": "300", "description": "Seconds per model for HPO"},
        {"name": "OPTUNA_N_TRIALS", "default": "50", "description": "Max trials per model"},
    ],
    scaffold_learning=True,
)


# ---------------------------------------------------------------------------
# Web domain config — drawn from examples/web-app
# ---------------------------------------------------------------------------

_WEB_SKILLS = [
    SkillDef(
        id="scaffold",
        name="Scaffold Feature",
        version="1.0.0",
        description="Generate boilerplate for a new feature: migration, route, component, test. Use when starting a new feature or the user says 'add feature X'. Creates all necessary stubs and file structure.",
        stage=1,
        phase="setup",
        inputs_required=[
            {"name": "feature_name", "type": "string",
             "description": "Name of the feature to scaffold"},
            {"name": "needs_db", "type": "bool",
             "description": "Whether a database migration is needed"},
        ],
        outputs=[
            {"name": "files_created", "type": "list[str]",
             "description": "Paths of generated files"},
        ],
        trigger_command="npx plop feature {name}",
        error_strategy="fail-fast",
        code_primary="plopfile.ts",
        tags=["scaffolding", "code-generation"],
        blocks=["implement"],
        negative_triggers=["Do NOT use for modifying existing features", "Do NOT use for bug fixes"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["src/**", "tests/**", "migrations/**"]}, "network": False},
        runbook_purpose="Generate all boilerplate files for a new feature: migration, API route, UI component, and test stubs.",
        runbook_when="- Starting a new feature\n- User says \"add feature X\"",
        runbook_how="1. Create migration file if DB changes needed\n2. Create API route with auth middleware\n3. Create React component (server or client)\n4. Create test files (unit + integration)\n5. Update feature flag env var",
        runbook_decision_tree="New feature request:\n  |- Needs DB? -> Create migration first\n  |- Needs API? -> Create route with withAuth middleware\n  |- Needs UI? -> Create component (server-first)\n  \\- Always -> Create test stubs",
        runbook_error_handling="- **Template error**: Fail fast, fix template\n- **Migration conflict**: Resolve before continuing",
    ),
    SkillDef(
        id="implement",
        name="Implement Feature",
        version="1.0.0",
        description="Write migration, routes, components, and feature flag integration. Use after scaffold creates boilerplate files and feature requirements are clear. Populates all scaffolded stubs with business logic.",
        stage=2,
        phase="development",
        inputs_required=[
            {"name": "feature_name", "type": "string",
             "description": "Name of the feature to implement"},
            {"name": "files_created", "type": "list[str]",
             "description": "Scaffold output files to populate"},
        ],
        outputs=[
            {"name": "files_modified", "type": "list[str]",
             "description": "Paths of files modified during implementation"},
        ],
        trigger_command="npm run dev",
        error_strategy="fail-fast",
        code_primary="src/",
        tags=["development", "implementation"],
        depends_on=["scaffold"],
        blocks=["test"],
        negative_triggers=["Do NOT use before scaffold has run", "Do NOT use without clear requirements"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["src/**", "tests/**", "migrations/**"]}, "network": False},
        runbook_purpose="Implement the feature by writing migration logic, API routes, UI components, and wiring up the feature flag.",
        runbook_when="- After scaffold creates boilerplate files\n- Feature requirements are clear",
        runbook_how="1. Write database migration (if needed)\n2. Implement API route with business logic and auth middleware\n3. Build React component (server-first, client when interactive)\n4. Wire up feature flag for gradual rollout\n5. Verify dev server runs without errors",
        runbook_decision_tree="For each scaffolded file:\n  |- Migration file? -> Write schema changes, add rollback\n  |- API route? -> Add business logic, input validation, auth\n  |- Component? -> Implement UI, add loading/error states\n  \\- All files populated? -> Run dev server to verify",
        runbook_error_handling="- **Type error**: Fix before moving to tests\n- **Migration conflict**: Resolve with existing migrations\n- **Dev server crash**: Check imports and dependencies",
    ),
    SkillDef(
        id="test",
        name="Run Tests",
        version="1.0.0",
        description="Run unit, integration, and e2e test suites. Use after implementation is complete and before deployment. Supports Jest, React Testing Library, Supertest, and Playwright.",
        stage=3,
        phase="quality",
        inputs_optional=[
            {"name": "suite", "type": "string", "default": "all",
             "description": "Which suite: unit, integration, e2e, or all"},
        ],
        outputs=[
            {"name": "results", "type": "object",
             "description": "Test pass/fail counts"},
        ],
        trigger_command="npm run test",
        error_strategy="fail-fast",
        code_primary="jest.config.ts",
        tags=["testing", "quality"],
        depends_on=["implement"],
        blocks=["review"],
        negative_triggers=["Do NOT use during active implementation — wait until code compiles"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["tests/**"]}, "network": False},
        runbook_purpose="Run the full test suite to verify feature quality before deployment.",
        runbook_when="- After implementation complete\n- Before deployment",
        runbook_how="1. Unit tests: Jest + React Testing Library\n2. Integration tests: Supertest against Express API\n3. E2E tests: Playwright against running dev server",
        runbook_decision_tree="Run unit tests\n  |- Fails? -> Fix before continuing\n  \\- Passes? -> Run integration tests\n      |- Fails? -> Fix API route or middleware\n      \\- Passes? -> Run e2e tests\n          |- Fails? -> Fix UI interaction\n          \\- All pass? -> Ready for deployment",
        runbook_error_handling="- **Test failure**: Fix before continuing to next suite\n- **Timeout**: Check for hanging async operations",
    ),
    SkillDef(
        id="review",
        name="Code Review",
        version="1.0.0",
        description="Run linting, type checking, bundle analysis, and security scan. Use after all tests pass and before deployment to staging. Catches code quality and security issues.",
        stage=4,
        phase="quality",
        inputs_required=[
            {"name": "feature_name", "type": "string",
             "description": "Name of the feature under review"},
        ],
        outputs=[
            {"name": "review_passed", "type": "bool",
             "description": "Whether all review checks passed"},
            {"name": "issues", "type": "list[str]",
             "description": "List of issues found during review"},
        ],
        trigger_command="npm run lint && npm run typecheck",
        error_strategy="fail-fast",
        code_primary="eslint.config.js",
        tags=["review", "linting", "security"],
        depends_on=["test"],
        blocks=["deploy"],
        negative_triggers=["Do NOT use before tests pass", "Do NOT use for runtime debugging"],
        allowed_tools={"shell": True, "files": {"read": True, "write": False}, "network": False},
        runbook_purpose="Run automated code quality checks: linting, type checking, bundle size analysis, and security scanning.",
        runbook_when="- After all tests pass\n- Before deployment to staging",
        runbook_how="1. Run ESLint with project rules\n2. Run TypeScript type checker (strict mode)\n3. Analyze bundle size for regressions\n4. Run npm audit for security vulnerabilities\n5. Collect all issues into a report",
        runbook_decision_tree="Run lint:\n  |- Errors? -> Fix before continuing\n  \\- Clean? -> Run typecheck\n      |- Type errors? -> Fix before continuing\n      \\- Clean? -> Check bundle size\n          |- >10% increase? -> Investigate, optimize\n          \\- Acceptable? -> Run security scan\n              |- Critical vulns? -> Fix before deploy\n              \\- Clean? -> Review passed",
        runbook_error_handling="- **Lint errors**: Must fix, cannot deploy with lint errors\n- **Type errors**: Must fix, strict mode is non-negotiable\n- **Security vulnerability**: Critical = block, moderate = warn",
    ),
    SkillDef(
        id="deploy",
        name="Deploy",
        version="1.0.0",
        description="Deploy to staging or production environment. Use after review passes all checks. Runs build, migrations, deploy, health check, and post-deploy monitoring.",
        stage=5,
        phase="delivery",
        inputs_required=[
            {"name": "environment", "type": "string",
             "description": "Target: staging or production"},
        ],
        trigger_command="npm run deploy:{environment}",
        error_strategy="fail-fast",
        code_primary="deploy.config.ts",
        tags=["deployment", "ci-cd"],
        depends_on=["review"],
        negative_triggers=["Do NOT deploy to production without staging verification first", "Do NOT use when tests or review have not passed"],
        allowed_tools={"shell": True, "files": {"read": True, "write": False}, "network": True},
        runbook_purpose="Deploy the application to staging or production.",
        runbook_when="- All tests pass\n- Feature reviewed and approved",
        runbook_how="1. Build production bundle\n2. Run database migrations\n3. Deploy to target environment\n4. Verify health check\n5. Monitor error rates for 15 minutes",
        runbook_decision_tree="Deploy to staging\n  |- Health check fails? -> Rollback, investigate\n  |- Error rate spikes? -> Rollback, investigate\n  \\- Stable for 15 min? -> Promote to production (with confirmation)",
        runbook_error_handling="- **Build failure**: Abort deploy\n- **Health check failure**: Rollback immediately\n- **Error rate spike**: Rollback and investigate",
    ),
]

_WEB_WORKFLOW = WorkflowDef(
    id="feature-lifecycle",
    entity="feature",
    description="Feature development from planning through deployment",
    states=[
        WorkflowStateDef("planned", "Requirements understood, ready to build", initial=True),
        WorkflowStateDef("in-progress", "Implementation underway", active=True),
        WorkflowStateDef("testing", "All tests running"),
        WorkflowStateDef("staging", "Deployed to staging for verification"),
        WorkflowStateDef("deployed", "Live in production", terminal=True),
        WorkflowStateDef("blocked", "Cannot proceed due to dependency or issue", terminal=True),
    ],
    transitions=[
        WorkflowTransitionDef("planned", "in-progress", skill="scaffold",
                              conditions=["Requirements are clear"]),
        WorkflowTransitionDef("in-progress", "testing", skill="implement",
                              conditions=["Implementation complete", "Code compiles without errors"]),
        WorkflowTransitionDef("testing", "staging", skill="review",
                              conditions=["All tests pass", "Code review passes"]),
        WorkflowTransitionDef("staging", "deployed", skill="deploy",
                              conditions=["Health check passes", "Error rate normal",
                                          "User confirms promotion"]),
        WorkflowTransitionDef("testing", "in-progress",
                              conditions=["Tests fail"],
                              description="Fix failing tests"),
    ],
)

WEB_CONFIG = DomainConfig(
    mode="dev-assist",
    workflow_commands=[
        CommandDef(
            id="build",
            trigger="/build",
            description="Build a feature end-to-end: scaffold, implement, test, review, deploy",
            runbook_purpose="Guide the agent through the full feature development lifecycle. The agent scaffolds boilerplate, implements the feature, runs tests, reviews code quality, and deploys.",
            worker_specialty="Building web features end-to-end — scaffold, implement, test, deploy",
            runbook_phases=[
                {"title": "Scaffold", "content": "Generate migration, route, component, and test stubs for the feature."},
                {"title": "Implement", "content": "Write migration logic, API routes, UI components, and wire up feature flags."},
                {"title": "Test", "content": "Run unit, integration, and e2e test suites. Fix failures before proceeding."},
                {"title": "Review", "content": "Run linting, type checking, bundle analysis, and security scan."},
                {"title": "Deploy", "content": "Deploy to staging, verify health checks, then promote to production."},
            ],
        ),
    ],
    instructions_description="Full-stack web application with authentication, billing, and real-time updates.",
    instructions_quick_ref="<!-- AGENT: Extract commands from package.json scripts, Makefile, or equivalent. Show the 3-5 most common commands for dev server, testing, migrations, and deployment. -->",
    instructions_project_structure="<!-- AGENT: Run directory listing and annotate key directories. Typical web app structure: pages/routes, components, API layer, database/ORM, auth, billing, tests. -->",
    instructions_rules=[
        "**Auth on every API route** -- use auth middleware consistently. No unprotected endpoints.",
        "**Feature flags** -- new features behind feature flags until stable.",
    ],
    instructions_workflow_phases=[
        {"title": "Understand Requirements", "content": "What does the feature do? What data does it need? How does it interact with existing features?"},
        {"title": "Implement", "content": "Schema migration -> API route -> UI component -> tests."},
        {"title": "Test (DO NOT SKIP)", "content": "Unit tests pass, integration tests pass, manual QA on staging."},
        {"title": "Deploy", "content": "Staging first, verify metrics, then production."},
    ],
    instructions_key_principle="Ship incrementally. Every feature has a migration, tests, and feature flag before going to production.",
    instructions_gotchas=[],
    skills=_WEB_SKILLS,
    orchestrator_pipeline="scaffold -> implement -> test -> review -> deploy",
    orchestrator_status_flow="planned -> in_progress -> testing -> staging -> deployed\n                                                 /\n                                          blocked (any stage)",
    orchestrator_decision_tree="FIRST: Check if pipeline is already complete (all items at terminal status).\n  If complete -> report status summary, ask user: re-run / new session / re-validate / exit.\n  If not -> proceed:\n\n1. Understand feature requirements\n2. Create migration if schema change needed\n3. Implement API route with auth middleware\n4. Implement UI component (server-first, client when interactive)\n5. Write tests (unit + integration + e2e)\n6. Deploy to staging\n7. Verify on staging (manual + automated checks)\n8. Deploy to production behind feature flag\n9. Monitor metrics, then remove flag",
    orchestrator_when_to_stop="- Feature deployed and stable in production\n- Feature flag removed after verification\n- All tests passing on main branch",
    workflow=_WEB_WORKFLOW,
    permissions_shell_read=[],
    permissions_shell_execute=[
        "npm run *",
        "npx *",
        "node *",
    ],
    permissions_file_write=[
        "src/**",
        "tests/**",
    ],
    permissions_deny_shell=[
        "rm -rf *",
        "DROP DATABASE *",
    ],
    permissions_confirm_shell=[
        "npm run deploy:*",
        "git push *",
        "npx drizzle-kit push *",
    ],
    permissions_confirm_actions=["deploy_production", "modify_billing"],
    env_required=[
        {"name": "DATABASE_URL", "description": "PostgreSQL connection string"},
        {"name": "STRIPE_SECRET_KEY", "description": "Stripe API key for billing"},
    ],
    env_optional=[
        {"name": "NODE_ENV", "default": "development", "description": "Runtime environment"},
    ],
)


# ---------------------------------------------------------------------------
# DevOps domain config — drawn from examples/devops
# ---------------------------------------------------------------------------

_DEVOPS_SKILLS = [
    SkillDef(
        id="provision",
        name="Provision Infrastructure",
        version="1.0.0",
        description="Create or update cloud infrastructure via Terraform. Use when new infrastructure is needed or existing resources require scaling. Always previews changes with plan before applying.",
        stage=1,
        phase="infrastructure",
        inputs_required=[
            {"name": "service", "type": "string",
             "description": "Service to provision"},
        ],
        inputs_environment=["AWS_PROFILE"],
        trigger_command="terraform plan && terraform apply",
        error_strategy="fail-fast",
        code_primary="terraform/",
        tags=["terraform", "infrastructure", "aws"],
        blocks=["configure"],
        negative_triggers=[
            "Do NOT use for configuration management — use configure skill instead",
            "Do NOT apply destructive changes without user confirmation",
        ],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["terraform/**"]}, "network": True},
        runbook_purpose="Create or update cloud infrastructure using Terraform.",
        runbook_when="- New service needs infrastructure\n- Existing service needs scaling or config change",
        runbook_how="1. `terraform plan -out=plan.tfplan` -- preview all changes\n2. Review plan for destructive actions (destroy, replace)\n3. `terraform apply plan.tfplan` -- apply only after review\n4. Verify resources created via `terraform state list`",
        runbook_decision_tree="terraform plan\n  |- No changes? -> Skip (already up to date)\n  |- Only additions? -> Safe to apply\n  |- Modifications? -> Review carefully, apply if benign\n  \\- Destructions? -> STOP -- confirm with user before applying",
        runbook_error_handling="- **Plan error**: Fix config before proceeding\n- **Apply error**: Check state, do NOT retry blindly",
    ),
    SkillDef(
        id="configure",
        name="Configure Service",
        version="1.0.0",
        description="Apply service configuration via Ansible with dry-run verification. Use after infrastructure is provisioned or when configuration changes are needed. Always runs --check mode first.",
        stage=2,
        phase="configuration",
        inputs_required=[
            {"name": "service", "type": "string",
             "description": "Service to configure"},
            {"name": "environment", "type": "string",
             "description": "Target environment"},
        ],
        inputs_environment=["ANSIBLE_VAULT_PASSWORD"],
        outputs=[
            {"name": "configured_services", "type": "list[str]",
             "description": "Services that were successfully configured"},
        ],
        trigger_command="ansible-playbook -i inventory configure.yml --limit {service}",
        error_strategy="fail-fast",
        code_primary="ansible/",
        tags=["ansible", "configuration", "automation"],
        depends_on=["provision"],
        blocks=["deploy"],
        negative_triggers=[
            "Do NOT use before infrastructure is provisioned",
            "Do NOT skip dry-run verification",
        ],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["ansible/**"]}, "network": True},
        runbook_purpose="Apply service configuration using Ansible playbooks after infrastructure is provisioned.",
        runbook_when="- Infrastructure provisioned (Terraform applied)\n- Configuration changes needed\n- New service setup",
        runbook_how="1. Run `ansible-playbook --check` for dry-run preview\n2. Review changes for unexpected modifications\n3. Apply configuration with `ansible-playbook`\n4. Verify services are running with correct config\n5. Advance to `configured`",
        runbook_decision_tree="Dry-run playbook:\n  |- No changes? -> Skip (already configured)\n  |- Expected changes only? -> Apply\n  |- Unexpected changes? -> STOP, investigate\n  \\- After apply:\n      |- Service healthy? -> Status: configured\n      \\- Service unhealthy? -> Rollback config, investigate",
        runbook_error_handling="- **Vault password missing**: Abort, cannot decrypt secrets\n- **Playbook error**: Fix playbook before retrying\n- **Service unhealthy after config**: Rollback to previous config",
    ),
    SkillDef(
        id="deploy",
        name="Deploy Service",
        version="1.0.0",
        description="Blue-green deploy with health checks and monitoring. Use when a new version is ready and staging has been verified. Supports rollback on health check failure or error rate spike.",
        stage=3,
        phase="delivery",
        inputs_required=[
            {"name": "service", "type": "string",
             "description": "Service to deploy"},
            {"name": "environment", "type": "string",
             "description": "Target: staging or production"},
        ],
        inputs_environment=["DEPLOY_ENV"],
        trigger_command="python scripts/manage.py deploy --service {service} --env {environment}",
        error_strategy="fail-fast",
        code_primary="scripts/manage.py",
        tags=["deployment", "blue-green"],
        depends_on=["configure"],
        negative_triggers=[
            "Do NOT deploy to production without staging verification",
            "Do NOT use when infrastructure is not provisioned",
        ],
        allowed_tools={"shell": True, "files": {"read": True, "write": False}, "network": True},
        runbook_purpose="Deploy a service using blue-green strategy with health checks.",
        runbook_when="- Infrastructure provisioned\n- New version ready to ship\n- Staging verified (for production deploys)",
        runbook_how="1. Build new container image\n2. Deploy to \"green\" target\n3. Run health checks against green\n4. Switch traffic from blue to green\n5. Monitor for 5 minutes\n6. Tear down old blue (or keep for rollback)",
        runbook_decision_tree="Deploy green instance\n  |- Build fails? -> Abort, fix build\n  |- Health check fails? -> Abort, keep blue\n  |- Traffic switch\n  |   |- Error rate spikes? -> Rollback to blue immediately\n  |   \\- All healthy for 5 min? -> Confirm deploy, tear down blue",
        runbook_error_handling="- **Build failure**: Abort immediately\n- **Health check failure**: Keep previous deployment\n- **Error rate spike**: Rollback to blue",
    ),
    SkillDef(
        id="rollback",
        name="Rollback Service",
        version="1.0.0",
        description="Rollback a service to the previous known-good deployment. Use when error rates spike after deploy, health checks fail, or user requests emergency rollback. Preserves failed deployment for debugging.",
        stage=4,
        phase="recovery",
        inputs_required=[
            {"name": "service", "type": "string",
             "description": "Service to rollback"},
            {"name": "environment", "type": "string",
             "description": "Target environment"},
        ],
        trigger_command="python scripts/manage.py rollback --service {service} --env {environment}",
        error_strategy="fail-fast",
        code_primary="scripts/manage.py",
        tags=["rollback", "recovery", "incident-response"],
        negative_triggers=[
            "Do NOT use when no previous deployment exists — escalate to human instead",
        ],
        allowed_tools={"shell": True, "files": {"read": True, "write": False}, "network": True},
        runbook_purpose="Revert a service to the previous known-good deployment immediately.",
        runbook_when="- Error rate spikes after deploy\n- Health checks fail after deploy\n- User requests emergency rollback",
        runbook_how="1. Identify previous deployment (blue instance)\n2. Switch traffic back to previous\n3. Verify health of reverted service\n4. Log rollback event with reason\n5. Keep failed deployment for debugging",
        runbook_decision_tree="Rollback initiated\n  |- Previous deployment available? -> Switch traffic\n  |   |- Health check passes? -> Rollback successful\n  |   \\- Health check fails? -> ESCALATE to human\n  \\- No previous deployment? -> ESCALATE to human",
        runbook_error_handling="- **No previous deployment**: Escalate to human\n- **Health check failure after rollback**: Escalate immediately",
    ),
    SkillDef(
        id="monitor",
        name="Monitor Service",
        version="1.0.0",
        description="Check health endpoints, error rates, latency, and resource usage. Use after deploy completes, after rollback to verify recovery, or on-demand health check requests. Reports healthy, degraded, or unhealthy status.",
        stage=5,
        phase="observability",
        inputs_required=[
            {"name": "service", "type": "string",
             "description": "Service to monitor"},
            {"name": "environment", "type": "string",
             "description": "Target environment"},
        ],
        inputs_optional=[
            {"name": "duration_seconds", "type": "int", "default": "300",
             "description": "How long to monitor in seconds"},
        ],
        outputs=[
            {"name": "health_status", "type": "str",
             "description": "Overall health: healthy, degraded, or unhealthy"},
            {"name": "metrics_summary", "type": "object",
             "description": "Summary of collected metrics"},
        ],
        trigger_command="python scripts/manage.py monitor --service {service} --env {environment}",
        error_strategy="per-item-isolation",
        code_primary="monitoring/",
        tags=["monitoring", "observability", "health-checks"],
        depends_on=["deploy"],
        negative_triggers=[
            "Do NOT use as a substitute for proper monitoring infrastructure",
        ],
        allowed_tools={"shell": True, "files": {"read": True, "write": False}, "network": True},
        runbook_purpose="Monitor a deployed service by checking health endpoints, error rates, latency percentiles, and resource usage.",
        runbook_when="- After deploy completes successfully\n- After rollback to verify recovery\n- On-demand health check requested",
        runbook_how="1. Poll health endpoint every 10 seconds\n2. Collect error rate from logs/metrics\n3. Measure latency p50, p95, p99\n4. Check CPU and memory usage\n5. Compare against thresholds for duration\n6. Report final health status",
        runbook_decision_tree="Monitor for duration_seconds:\n  |- Health endpoint down? -> Status: unhealthy\n  |- Error rate > 1%? -> Status: degraded\n  |- Latency p99 > threshold? -> Status: degraded\n  |- CPU > 80% or Memory > 85%? -> Status: degraded\n  \\- All metrics normal? -> Status: healthy\n\nAfter monitoring:\n  |- Healthy? -> Confirm deployment\n  |- Degraded? -> Trigger rollback consideration\n  \\- Unhealthy? -> Immediate rollback",
        runbook_error_handling="- **Health endpoint unreachable**: Mark unhealthy immediately\n- **Metrics collection failure**: Log warning, continue with available data\n- **Threshold breach**: Alert and recommend rollback",
    ),
]

_DEVOPS_WORKFLOW = WorkflowDef(
    id="service-lifecycle",
    entity="service",
    description="Service deployment lifecycle with monitoring and rollback",
    states=[
        WorkflowStateDef("planned", "Infrastructure design approved", initial=True),
        WorkflowStateDef("provisioning", "Terraform creating resources", active=True),
        WorkflowStateDef("configured", "Ansible config applied"),
        WorkflowStateDef("deploying", "Blue-green deploy in progress", active=True),
        WorkflowStateDef("deployed", "Service live and receiving traffic", terminal=True),
        WorkflowStateDef("degraded", "Service live but metrics abnormal"),
        WorkflowStateDef("rolled-back", "Reverted to previous version"),
        WorkflowStateDef("failed", "Deployment failed, no traffic switched", terminal=True),
    ],
    transitions=[
        WorkflowTransitionDef("planned", "provisioning", skill="provision",
                              conditions=["Terraform plan reviewed"]),
        WorkflowTransitionDef("provisioning", "configured", skill="configure",
                              conditions=["All resources created", "Health checks pass"],
                              on_failure="failed"),
        WorkflowTransitionDef("configured", "deploying", skill="deploy",
                              conditions=["Tests pass in staging"]),
        WorkflowTransitionDef("deploying", "deployed",
                              conditions=["Health check passes",
                                          "Error rate < 1% for 5 min"],
                              on_failure="failed"),
        WorkflowTransitionDef("deployed", "degraded",
                              conditions=["Error rate > 1% or latency p99 > threshold"]),
        WorkflowTransitionDef("degraded", "rolled-back", skill="rollback",
                              conditions=["Degradation confirmed"]),
        WorkflowTransitionDef("rolled-back", "deploying", skill="deploy",
                              conditions=["Fix applied and tested"],
                              description="Re-deploy after fixing the issue"),
    ],
)

DEVOPS_CONFIG = DomainConfig(
    mode="dev-assist",
    workflow_commands=[
        CommandDef(
            id="provision",
            trigger="/provision",
            description="Provision and deploy infrastructure: provision, configure, deploy",
            runbook_purpose="Guide the agent through the full infrastructure provisioning and deployment lifecycle. The agent provisions resources via Terraform, configures services via Ansible, and deploys with blue-green strategy.",
            worker_specialty="Provisioning and deploying infrastructure — Terraform, Ansible, blue-green deploys",
            runbook_phases=[
                {"title": "Provision", "content": "Run terraform plan, review for destructive changes, then apply."},
                {"title": "Configure", "content": "Apply Ansible playbooks with dry-run verification first."},
                {"title": "Deploy", "content": "Blue-green deploy with health checks. Monitor for 5 minutes. Rollback if degraded."},
            ],
        ),
    ],
    instructions_description="Infrastructure automation — provision, configure, deploy, monitor, and rollback.",
    instructions_quick_ref="<!-- AGENT: Extract commands from scripts/, Makefile, or CI config. Show the 3-5 most common commands for planning, applying, deploying, and rolling back. -->",
    instructions_project_structure="<!-- AGENT: Run directory listing and annotate key directories. Typical infrastructure structure: IaC definitions, configuration management, deployment scripts, monitoring, container definitions. -->",
    instructions_rules=[
        "**Never apply without preview** -- always preview infrastructure changes before applying.",
        "**Staging first** -- every change hits staging before production.",
        "**Rollback ready** -- every deploy must have a tested rollback path.",
        "**No hardcoded secrets** -- use a secrets manager. Never commit credentials.",
        "**Tag everything** -- all resources tagged with service, environment, owner.",
    ],
    instructions_workflow_phases=[
        {"title": "Verify Prerequisites", "content": "Check: image built, tests pass, staging healthy, rollback tested."},
        {"title": "Deploy to Staging", "content": "Blue-green deployment, health check, smoke tests."},
        {"title": "Monitor (DO NOT SKIP)", "content": "Watch error rates, latency p99, CPU/memory for 5 minutes."},
        {"title": "Promote or Rollback", "content": "If metrics stable -> promote to production. If metrics degrade -> immediate rollback."},
    ],
    instructions_key_principle="Infrastructure changes are permanent and visible. Measure twice, apply once. Always have a rollback plan.",
    instructions_gotchas=[],
    skills=_DEVOPS_SKILLS,
    orchestrator_pipeline="provision -> configure -> deploy -> monitor -> verify",
    orchestrator_status_flow="planned -> provisioning -> configured -> deploying -> deployed -> monitored\n                                          |            |\n                                       failed      degraded -> rollback -> deployed",
    orchestrator_decision_tree="FIRST: Check if pipeline is already complete (all items at terminal status).\n  If complete -> report status summary, ask user: re-run / new session / re-validate / exit.\n  If not -> proceed:\n\n1. Provision infrastructure (Terraform)\n   |- Plan shows destructive changes? -> STOP, confirm with user\n   \\- Plan is additive? -> Apply\n2. Configure services (Ansible)\n   |- Dry-run shows unexpected changes? -> STOP, investigate\n   \\- Dry-run clean? -> Apply\n3. Deploy service (blue-green)\n   |- Health check fails? -> Rollback immediately\n   |- Error rate > 1%? -> Rollback immediately\n   \\- All healthy? -> Mark deployed\n4. Monitor for 5 minutes\n   |- Metrics degrade? -> Rollback\n   \\- Stable? -> Confirm deployment",
    orchestrator_when_to_stop="- Service deployed and metrics stable\n- Rollback completed successfully\n- Escalation required (human intervention needed)",
    workflow=_DEVOPS_WORKFLOW,
    permissions_shell_read=[
        "terraform plan *",
        "terraform state list *",
        "ansible-inventory *",
        "docker ps *",
        "kubectl get *",
    ],
    permissions_shell_execute=[
        "python scripts/manage.py *",
        "ansible-playbook --check *",
    ],
    permissions_file_write=[
        "terraform/**/*.tf",
        "ansible/**/*.yml",
    ],
    permissions_deny_shell=[
        "terraform destroy *",
        "rm -rf *",
        "kubectl delete namespace *",
    ],
    permissions_confirm_shell=[
        "terraform apply *",
        "ansible-playbook *",
        "python scripts/manage.py deploy --env production *",
        "python scripts/manage.py rollback *",
    ],
    permissions_confirm_actions=["deploy_production", "scale_down", "destroy_resource"],
    env_required=[
        {"name": "AWS_PROFILE", "description": "AWS credentials profile"},
        {"name": "DEPLOY_ENV", "description": "Target environment (staging/production)"},
    ],
    env_optional=[
        {"name": "ROLLBACK_WINDOW", "default": "300", "description": "Seconds to monitor before confirming deploy"},
    ],
)


# ---------------------------------------------------------------------------
# Research domain config — agent-integrated content processing
# ---------------------------------------------------------------------------

_RESEARCH_SKILLS = [
    SkillDef(
        id="ingest",
        name="Ingest Content",
        version="1.0.0",
        description="Collect papers and content from sources (arXiv, Semantic Scholar, RSS, web). Use when the pipeline needs fresh content or no items are in ingested status. Deduplicates by DOI, URL, and title similarity.",
        stage=1,
        phase="ingestion",
        inputs_required=[
            {"name": "sources", "type": "list[str]",
             "description": "Content sources to query (URLs, search terms, feed URLs)"},
        ],
        inputs_optional=[
            {"name": "max_items", "type": "int", "default": "50",
             "description": "Maximum items to ingest per run"},
            {"name": "date_range", "type": "str", "default": "7d",
             "description": "How far back to look (e.g. 7d, 30d, 1y)"},
        ],
        outputs=[
            {"name": "ingested_ids", "type": "list[str]",
             "description": "IDs of newly ingested items"},
        ],
        trigger_command="python scripts/pipeline.py --stage ingest",
        error_strategy="per-item-isolation",
        code_primary="pipeline/ingest.py",
        tags=["ingestion", "arxiv", "semantic-scholar", "rss"],
        blocks=["parse"],
        negative_triggers=["Do NOT use for manual document upload — add files directly to data/"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "data/**"]}, "network": True},
        runbook_purpose="Collect new papers, articles, and content from configured sources.",
        runbook_when="- No items in `ingested` status\n- User requests new content\n- Scheduled daily/weekly",
        runbook_how="1. Query each configured source (arXiv API, Semantic Scholar, RSS feeds, web scraping)\n2. Deduplicate against existing records by DOI, URL, or title similarity\n3. Store raw content with source metadata\n4. Record provenance and access timestamps",
        runbook_decision_tree="For each source:\n  |- API available? -> Query API with filters\n  |- RSS feed? -> Parse feed entries\n  |- Web URL? -> Fetch and extract content\n  \\- For each item:\n      |- Already exists? -> Skip\n      |- Matches topic filters? -> Ingest\n      \\- No match? -> Skip",
        runbook_error_handling="- **API rate limit**: Back off and retry\n- **Network error**: Skip source, continue with others\n- **Duplicate detected**: Skip silently",
    ),
    SkillDef(
        id="parse",
        name="Parse Content",
        version="1.0.0",
        description="Extract structure, metadata, key sections, and citations from raw content. Use after ingest when items reach ingested status. Supports PDF, HTML, and plain text formats.",
        stage=2,
        phase="extraction",
        inputs_required=[
            {"name": "item_id", "type": "str",
             "description": "ID of item to parse"},
        ],
        outputs=[
            {"name": "parsed_content", "type": "object",
             "description": "Structured representation with sections, metadata, citations"},
        ],
        trigger_command="python scripts/pipeline.py --stage parse --item-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/parse.py",
        tags=["parsing", "extraction", "metadata"],
        depends_on=["ingest"],
        blocks=["analyze"],
        negative_triggers=["Do NOT use on already-parsed items"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "data/**"]}, "network": False},
        runbook_purpose="Extract structured information from raw ingested content: title, authors, abstract, sections, figures, citations, and metadata.",
        runbook_when="- Item is at `ingested` status\n- After ingest skill completes",
        runbook_how="1. Detect content type (PDF, HTML, plain text)\n2. Extract metadata: title, authors, date, DOI, venue\n3. Extract key sections: abstract, introduction, methods, results, conclusion\n4. Extract citations and build reference list\n5. Extract figures/tables if present\n6. Advance to `parsed`",
        runbook_decision_tree="Detect format:\n  |- PDF? -> Use PDF parser (PyMuPDF/pdfplumber)\n  |- HTML? -> Use BeautifulSoup/trafilatura\n  |- Plain text? -> Use regex-based extraction\n  \\- After extraction:\n      |- Missing title or abstract? -> Mark for manual review\n      \\- Complete? -> Status: \"parsed\"",
        runbook_error_handling="- **Corrupted PDF**: Reject with reason\n- **Encoding error**: Try fallback encodings\n- **Missing metadata**: Infer from content where possible",
    ),
    SkillDef(
        id="analyze",
        name="Analyze Content",
        version="1.0.0",
        description="Classify topics, extract insights, and identify key findings. Use after parse when items reach parsed status. Computes relevance scores and finds connections to existing knowledge.",
        stage=3,
        phase="analysis",
        inputs_required=[
            {"name": "item_id", "type": "str",
             "description": "ID of item to analyze"},
        ],
        outputs=[
            {"name": "topics", "type": "list[str]",
             "description": "Classified topic tags"},
            {"name": "key_findings", "type": "list[str]",
             "description": "Extracted key findings and insights"},
            {"name": "relevance_score", "type": "float",
             "description": "0.0-1.0 relevance to research focus"},
        ],
        trigger_command="python scripts/pipeline.py --stage analyze --item-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/analyze.py",
        tags=["analysis", "classification", "insights"],
        depends_on=["parse"],
        blocks=["organize"],
        negative_triggers=["Do NOT use on unparsed items — run parse first"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "data/**"]}, "network": False},
        runbook_purpose="Classify topics, extract key findings, compute relevance scores, and identify connections to existing knowledge.",
        runbook_when="- Item is at `parsed` status\n- After parse skill completes",
        runbook_how="1. Classify into topic taxonomy (multi-label)\n2. Extract key findings and contributions\n3. Identify methodology and approach\n4. Compute relevance score against research focus\n5. Find connections to previously analyzed items\n6. Advance to `analyzed`",
        runbook_decision_tree="Analyze parsed content:\n  |- Relevance score < 0.2? -> Reject: \"low_relevance\"\n  |- No identifiable findings? -> Reject: \"no_findings\"\n  |- Duplicate findings? -> Merge with existing, note source\n  \\- Valid analysis? -> Status: \"analyzed\"",
        runbook_error_handling="- **Ambiguous topic**: Assign multiple labels, flag for review\n- **Low confidence**: Lower relevance score, keep for manual review",
    ),
    SkillDef(
        id="organize",
        name="Organize Content",
        version="1.0.0",
        description="Categorize by topic and relevance, build taxonomy, cross-reference related items. Use after analyze when items reach analyzed status with relevance_score >= 0.2. Updates the knowledge graph.",
        stage=4,
        phase="taxonomy",
        inputs_required=[
            {"name": "item_id", "type": "str",
             "description": "ID of item to organize"},
        ],
        outputs=[
            {"name": "categories", "type": "list[str]",
             "description": "Assigned taxonomy categories"},
            {"name": "cross_refs", "type": "list[str]",
             "description": "IDs of related items"},
        ],
        trigger_command="python scripts/pipeline.py --stage organize --item-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/organize.py",
        tags=["taxonomy", "categorization", "cross-reference"],
        depends_on=["analyze"],
        blocks=["display"],
        negative_triggers=["Do NOT use on items below relevance threshold (relevance_score < 0.2)"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "data/**", "output/**"]}, "network": False},
        runbook_purpose="Place analyzed content into the knowledge taxonomy, cross-reference with related items, and update the knowledge graph.",
        runbook_when="- Item is at `analyzed` status\n- After analyze skill completes",
        runbook_how="1. Map topics to taxonomy categories\n2. Find related items by topic overlap and citation links\n3. Update knowledge graph with new connections\n4. Compute cluster membership\n5. Update category summaries\n6. Advance to `organized`",
        runbook_decision_tree="For analyzed item:\n  |- Fits existing category? -> Assign and cross-reference\n  |- New topic cluster? -> Create new category, assign\n  |- Contradicts existing findings? -> Flag for attention\n  \\- Organized? -> Status: \"organized\"",
        runbook_error_handling="- **Category conflict**: Assign to multiple, flag for review\n- **Missing cross-references**: Continue without, note gap",
    ),
    SkillDef(
        id="display",
        name="Display Results",
        version="1.0.0",
        description="Generate dashboard, report, or organized output for consumption. Use after organize completes or when user requests a summary. Supports markdown, HTML, and JSON output formats.",
        stage=5,
        phase="delivery",
        inputs_optional=[
            {"name": "format", "type": "str", "default": "markdown",
             "description": "Output format: markdown, html, json"},
            {"name": "focus_topics", "type": "list[str]",
             "description": "Topics to highlight in output"},
        ],
        outputs=[
            {"name": "report_path", "type": "str",
             "description": "Path to generated report"},
        ],
        trigger_command="python scripts/pipeline.py --stage display",
        error_strategy="fail-fast",
        code_primary="pipeline/display.py",
        tags=["reporting", "dashboard", "output"],
        depends_on=["organize"],
        negative_triggers=["Do NOT use when no items have been organized yet"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["output/**"]}, "network": False},
        runbook_purpose="Generate readable output: topic summaries, key findings digest, trend analysis, and cross-reference maps.",
        runbook_when="- After organize completes\n- User requests a report or summary",
        runbook_how="1. Gather all organized items by category\n2. Generate topic summaries with key findings\n3. Build trend analysis (new topics, growing areas)\n4. Create cross-reference visualization\n5. Output in requested format (markdown, HTML, JSON)",
        runbook_decision_tree="Generate report:\n  |- No organized items? -> Report: \"No content processed yet\"\n  |- Focus topics specified? -> Filter to those topics\n  \\- Full report? -> Include all categories with summaries",
        runbook_error_handling="- **Empty category**: Include with note \"no items yet\"\n- **Template error**: Fall back to plain text output",
    ),
]

_RESEARCH_WORKFLOW = WorkflowDef(
    id="content-pipeline",
    entity="content-item",
    description="Content processing pipeline from ingestion through organized display",
    states=[
        WorkflowStateDef("ingested", "Raw content collected from source", initial=True),
        WorkflowStateDef("parsed", "Structure and metadata extracted"),
        WorkflowStateDef("analyzed", "Topics classified, findings extracted", active=True),
        WorkflowStateDef("organized", "Categorized and cross-referenced"),
        WorkflowStateDef("displayed", "Included in generated output", terminal=True),
        WorkflowStateDef("rejected", "Failed quality checks or irrelevant", terminal=True),
    ],
    transitions=[
        WorkflowTransitionDef("ingested", "parsed", skill="parse",
                              conditions=["Content is accessible and readable"]),
        WorkflowTransitionDef("parsed", "analyzed", skill="analyze",
                              conditions=["Metadata extraction successful"]),
        WorkflowTransitionDef("analyzed", "organized", skill="organize",
                              conditions=["Relevance score >= 0.2", "Key findings extracted"]),
        WorkflowTransitionDef("organized", "displayed", skill="display",
                              conditions=["Category assigned", "Cross-references resolved"]),
        WorkflowTransitionDef("ingested", "rejected",
                              conditions=["Content unreadable or corrupted"],
                              description="Reject unprocessable content"),
        WorkflowTransitionDef("analyzed", "rejected",
                              conditions=["Relevance score < 0.2"],
                              description="Reject irrelevant content"),
    ],
)

RESEARCH_CONFIG = DomainConfig(
    mode="agent-integrated",
    workflow_commands=[
        CommandDef(
            id="build",
            trigger="/build",
            description="Build the research pipeline codebase from scratch: project structure, source adapters, storage, pipeline stages, taxonomy, scripts, tests",
            runbook_purpose="Construct the complete research content pipeline codebase. The agent creates project structure, implements source adapters, sets up storage, builds each pipeline stage, defines the topic taxonomy, adds CLI scripts, and verifies with tests.",
            worker_specialty="Constructing research pipeline codebases — sources, storage, stages, taxonomy",
            runbook_phases=[
                {"title": "Project Structure", "content": "Create directory layout: pipeline/, sources/, config/, output/, data/, scripts/, tests/. Set up pyproject.toml, __init__.py files, and virtual environment."},
                {"title": "Source Adapters", "content": "Implement source adapters: arxiv.py, semantic_scholar.py, rss.py, web.py. Each adapter handles authentication, rate limiting, and returns normalized content objects."},
                {"title": "Storage Layer", "content": "Set up SQLite or file-based storage for raw and processed content. Create schema for items, metadata, citations, and topic assignments. Add helper functions."},
                {"title": "Pipeline Stages", "content": "Build each stage module: ingest.py, parse.py, analyze.py, organize.py, display.py. Each reads items at current status, processes them, and advances status."},
                {"title": "Topic Taxonomy", "content": "Create config/topic_taxonomy.py — the classification hierarchy. Define top-level categories, subcategories, and keyword mappings. Taxonomy evolves as content is processed."},
                {"title": "Scripts & CLI", "content": "Build scripts/pipeline.py with --stage and --sources flags. Add convenience scripts for common operations (search, report generation)."},
                {"title": "Tests & Verification", "content": "Write unit tests for each pipeline stage and source adapter. Add integration test that runs ingest->parse->analyze on sample content. Verify all imports and CLI commands work."},
            ],
        ),
        CommandDef(
            id="process",
            trigger="/process",
            description="Run the content pipeline: ingest, parse, analyze, organize, display",
            runbook_purpose="Execute the complete content processing pipeline. The agent ingests content from sources, extracts structure, analyzes findings, organizes into taxonomy, and generates output.",
            worker_specialty="Processing research content through the pipeline — ingest, analyze, organize",
            runbook_phases=[
                {"title": "Ingest", "content": "Collect papers/articles from configured sources (arXiv, Semantic Scholar, RSS, web)."},
                {"title": "Parse", "content": "Extract structure, metadata, sections, and citations from raw content."},
                {"title": "Analyze", "content": "Classify topics, extract key findings, compute relevance scores."},
                {"title": "Organize", "content": "Categorize by topic, build taxonomy, cross-reference related items."},
                {"title": "Display", "content": "Generate reports, summaries, and visualizations of processed content."},
            ],
        ),
    ],
    instructions_description="Research content processing pipeline. Ingests papers and articles, extracts structure and metadata, analyzes findings, organizes by topic taxonomy, and generates reports.",
    instructions_quick_ref="<!-- AGENT: Extract commands from scripts/, Makefile, or pyproject.toml. Show the 3-5 most common commands for running the pipeline, ingesting sources, and generating output. -->",
    instructions_project_structure="<!-- AGENT: Run directory listing and annotate key directories. Typical research pipeline structure: pipeline stages, source adapters, configuration, output, data storage. -->",
    instructions_rules=[
        "**Source attribution** -- always record provenance and access date for every ingested item.",
        "**Deduplication** -- check by identifier, URL, and title similarity before ingesting.",
        "**Relevance filtering** -- reject items below the configured relevance threshold.",
        "**Incremental processing** -- resume from last completed stage, never reprocess completed items.",
        "**Structured output** -- all analysis results stored in structured format, not just prose.",
    ],
    instructions_workflow_phases=[
        {"title": "Ingest Sources", "content": "Query configured sources for new content matching topic filters."},
        {"title": "Extract Structure", "content": "Parse content into structured sections, metadata, and citations."},
        {"title": "Analyze & Classify", "content": "Topic classification, key finding extraction, relevance scoring."},
        {"title": "Organize & Connect", "content": "Build taxonomy, cross-reference, update knowledge graph."},
        {"title": "Generate Output", "content": "Produce reports, summaries, and dashboards in requested format."},
    ],
    instructions_key_principle="Content is the raw material; structured knowledge is the product. Every item flows through the pipeline from raw ingestion to organized, cross-referenced output.",
    instructions_gotchas=[],
    skills=_RESEARCH_SKILLS,
    orchestrator_pipeline="ingest -> parse -> analyze -> organize -> display",
    orchestrator_status_flow="ingested -> parsed -> analyzed -> organized -> displayed\n    |                  |\n    v                  v\n rejected           rejected",
    orchestrator_decision_tree="FIRST: Check if pipeline is already complete (all items at terminal status).\n  If complete -> report status summary, ask user: re-run / new session / re-validate / exit.\n  If not -> proceed:\n\nfor each stage in [ingest, parse, analyze, organize, display]:\n  1. Get items at current status\n  2. For each item:\n     a. Run stage skill\n     b. On success: advance status\n     c. On failure: log error, reject if unrecoverable\n  3. Report: N processed, N rejected, N skipped\n\nAfter analyze stage:\n  - Check relevance scores\n  - Reject items below threshold\n  - Flag items that contradict existing findings",
    orchestrator_when_to_stop="- All items at terminal status (displayed or rejected)\n- No new items from sources\n- User requests stop",
    workflow=_RESEARCH_WORKFLOW,
    permissions_shell_read=[
        "python scripts/pipeline.py status *",
        "python scripts/pipeline.py list *",
    ],
    permissions_shell_execute=[
        "python scripts/pipeline.py *",
        "python -m pytest *",
    ],
    permissions_file_write=[
        "pipeline/**/*.py",
        "config/**/*.py",
        "output/**",
        "data/**",
    ],
    permissions_deny_shell=[
        "rm -rf *",
    ],
    permissions_confirm_shell=[
        "git push *",
    ],
    permissions_confirm_actions=[],
    env_required=[],
    env_optional=[
        {"name": "SEMANTIC_SCHOLAR_API_KEY", "default": "", "description": "Semantic Scholar API key (optional, increases rate limits)"},
        {"name": "MAX_ITEMS_PER_RUN", "default": "50", "description": "Maximum items to process per pipeline run"},
    ],
    scaffold_learning=True,
)


# ---------------------------------------------------------------------------
# Generic agent-integrated base (used for Custom type in interactive picker)
# ---------------------------------------------------------------------------

_BUILD_COMMAND = CommandDef(
    id="build",
    trigger="/build",
    description="Build the project codebase: structure, core modules, storage, configuration, scripts, tests",
    runbook_purpose="Construct the project codebase from scratch. The agent creates directory structure, implements core modules, sets up storage, writes configuration, adds scripts, and verifies with tests.",
    worker_specialty="Constructing project codebases from scratch",
    runbook_phases=[
        {"title": "Project Structure", "content": "Create directory layout, set up package config, __init__.py files, and virtual environment or package manager."},
        {"title": "Core Modules", "content": "Implement the primary modules that define the system's behavior. Each module has a clear responsibility and interface."},
        {"title": "Storage & State", "content": "Set up database, file storage, or state management. Create schemas, migrations, and helper functions."},
        {"title": "Configuration", "content": "Create settings module with environment-based config. Define thresholds, endpoints, and operational parameters."},
        {"title": "Integration Layer", "content": "Wire modules together. Implement the main entry point and any API or CLI interfaces."},
        {"title": "Scripts & CLI", "content": "Build run scripts with appropriate flags and options. Add convenience scripts for common operations."},
        {"title": "Tests & Verification", "content": "Write unit tests for each module. Add integration test for the primary workflow. Verify all imports and commands work."},
    ],
)

DEV_ASSIST_BASE_CONFIG = DomainConfig(
    mode="dev-assist",
    workflow_commands=[_BUILD_COMMAND],
    instructions_description="",   # empty -> falls through to TODO scaffolding in template
)

AGENT_INTEGRATED_BASE_CONFIG = DomainConfig(
    mode="agent-integrated",
    workflow_commands=[
        _BUILD_COMMAND,
        CommandDef(
            id="run",
            trigger="/run",
            description="Execute the primary pipeline or workflow end-to-end",
            runbook_purpose="Run the project's main workflow from start to finish. The agent executes each stage, monitors progress, handles errors, and reports results.",
            worker_specialty="Executing the primary project workflow end-to-end",
            runbook_phases=[
                {"title": "Pre-flight Check", "content": "Verify environment, dependencies, and configuration. Ensure storage is accessible and previous state is consistent."},
                {"title": "Execute Pipeline", "content": "Run each stage of the pipeline in order. Monitor progress and resource usage. Handle per-item errors gracefully."},
                {"title": "Analyze Results", "content": "Check output quality, verify expected outcomes, and flag anomalies or failures."},
                {"title": "Report & Clean Up", "content": "Generate summary of results. Archive artifacts. Update state for next run."},
            ],
        ),
    ],
    instructions_description="",   # empty -> falls through to TODO scaffolding in template
    scaffold_learning=True,
)


# ---------------------------------------------------------------------------
# Public mapping
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Assistant domain config — personal AI assistant (OpenClaw target)
# ---------------------------------------------------------------------------

_ASSISTANT_SKILLS = [
    SkillDef(
        id="greeting",
        name="Greeting",
        version="1.0.0",
        description="Greet users warmly and contextually when they start a conversation or say hello. References time of day and user profile when available.",
        stage=1,
        phase="interaction",
        activation="auto",
        emoji="\U0001f44b",
        user_invocable=True,
        tags=["conversation", "onboarding"],
        negative_triggers=["Do NOT use mid-conversation or when the user is giving a command"],
        runbook_purpose="Greet the user warmly when they initiate a conversation or say hello.",
        runbook_when="- User sends a greeting (hello, hi, hey, good morning, etc.)\n- First message in a new session",
        runbook_how="1. Check time of day for contextual greeting\n2. Reference the user's name from USER.md if available\n3. Mention any pending heartbeat items if relevant\n4. Keep it brief — one or two sentences max",
    ),
    SkillDef(
        id="web-search",
        name="Web Search",
        version="1.0.0",
        description="Search the web using the Brave Search API when the user needs current information, news, or facts that may be beyond training data.",
        stage=1,
        phase="research",
        activation="explicit",
        emoji="\U0001f50d",
        user_invocable=True,
        requires_env=["BRAVE_API_KEY"],
        primary_env="BRAVE_API_KEY",
        mcp_server={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": "${BRAVE_API_KEY}"},
        },
        tags=["search", "web", "research"],
        negative_triggers=["Do NOT use for questions answerable from memory or context"],
        allowed_tools={"network": True},
        runbook_purpose="Search the web using the Brave Search API when the user needs current information.",
        runbook_when="- User asks about current events or recent information\n- User explicitly asks to search the web\n- Question requires facts beyond training data",
        runbook_how="1. Call the `brave_search` tool with a concise query\n2. Format results as a bulleted list with title, URL, and snippet\n3. Summarize the key findings in 2-3 sentences\n4. Cite sources with URLs",
        runbook_error_handling="- **API timeout**: Retry once, then inform user\n- **No results**: Suggest alternative search terms\n- **Rate limit**: Wait and retry (max 5 searches per turn)",
    ),
    SkillDef(
        id="calendar",
        name="Calendar Manager",
        version="1.0.0",
        description="Manage calendar events — create, list, update, and cancel meetings and reminders. Integrates with Google Calendar or similar providers.",
        stage=1,
        phase="productivity",
        activation="explicit",
        emoji="\U0001f4c5",
        user_invocable=True,
        tags=["calendar", "scheduling", "productivity"],
        negative_triggers=["Do NOT use for general time questions or timezone conversions"],
        runbook_purpose="Manage the user's calendar events and reminders.",
        runbook_when="- User asks to schedule, reschedule, or cancel a meeting\n- User asks about upcoming events\n- User wants to set a reminder",
        runbook_how="1. Parse the user's request for event details (title, time, duration, attendees)\n2. Confirm details with the user before creating/modifying\n3. Execute the calendar operation\n4. Confirm the result with event details",
    ),
    SkillDef(
        id="code-review",
        name="Code Review",
        version="1.0.0",
        description="Review code changes from GitHub pull requests or local diffs. Analyze for bugs, style issues, security concerns, and suggest improvements.",
        stage=1,
        phase="development",
        activation="explicit",
        emoji="\U0001f50d",
        user_invocable=True,
        requires_bins=["git"],
        tags=["code-review", "github", "development"],
        negative_triggers=["Do NOT use for writing new code from scratch"],
        allowed_tools={"shell": True, "files": {"read": True}, "network": True},
        runbook_purpose="Review code changes and provide constructive feedback.",
        runbook_when="- User shares a PR link or asks for a code review\n- User pastes code and asks for feedback\n- Heartbeat detects open PRs assigned to the user",
        runbook_how="1. Fetch the diff (from GitHub PR or local git diff)\n2. Analyze for bugs, security issues, and style violations\n3. Provide specific, actionable feedback with line references\n4. Summarize overall assessment (approve / request changes)",
    ),
]

_ASSISTANT_CONVERSE_COMMAND = CommandDef(
    id="converse",
    trigger="/converse",
    description="Start or resume a conversation session with the assistant",
    runbook_purpose="Run the assistant's main conversational loop. The agent listens across configured channels, responds to messages, executes skills on demand, and proactively checks heartbeat tasks.",
    worker_specialty="Multi-platform conversational AI assistant",
    runbook_phases=[
        {"title": "Session Setup", "content": "Load user profile from USER.md. Check HEARTBEAT.md for pending tasks. Review recent conversation history for context continuity."},
        {"title": "Message Processing", "content": "Receive messages from connected channels. Determine intent — is this a greeting, a question, a skill invocation, or a general conversation? Route accordingly."},
        {"title": "Skill Execution", "content": "When a skill is triggered (explicitly via command or automatically via context match), execute it and return results to the user."},
        {"title": "Memory & Wrap-up", "content": "Persist important learnings to MEMORY.md. Update AGENTS.md if the user's preferences or context changed."},
    ],
)

ASSISTANT_CONFIG = DomainConfig(
    mode="agent-integrated",
    workflow_commands=[_ASSISTANT_CONVERSE_COMMAND],

    # Identity defaults for scaffold
    identity_persona=(
        "You are a helpful, security-conscious personal assistant. "
        "You are concise, accurate, and proactive. You ask for clarification "
        "when instructions are ambiguous. You never share credentials or "
        "sensitive information across channels."
    ),
    identity_name="Assistant",
    identity_emoji="\U0001f99e",
    model_provider="anthropic",
    model_model="claude-sonnet-4-20250514",
    sandbox_enabled=False,
    sandbox_runtime="docker",
    heartbeat_interval=30,
    heartbeat_checklist=(
        "- Check for unread messages across channels\n"
        "- Review calendar for upcoming meetings (next 2 hours)\n"
        "- Check GitHub for open PRs assigned to user\n"
    ),
    channels={
        "telegram": {"enabled": "true", "bot_token_env": "TELEGRAM_BOT_TOKEN"},
        "discord": {"enabled": "true", "bot_token_env": "DISCORD_BOT_TOKEN"},
    },

    instructions_description="Personal AI assistant connected to messaging platforms via OpenClaw. Runs 24/7, responds across channels, and executes skills on demand.",
    instructions_quick_ref=(
        "```bash\n"
        "aes sync -t openclaw           # generate .openclaw/ config\n"
        "openclaw gateway               # start the agent daemon\n"
        "openclaw nemoclaw launch       # start with sandbox (if configured)\n"
        "```"
    ),
    instructions_rules=[
        "Never share API keys, tokens, or credentials in any channel",
        "Always confirm destructive actions (deleting events, sending bulk messages) before executing",
        "Keep responses concise — messaging platforms have character limits",
        "Respect user's quiet hours (check HEARTBEAT.md schedule)",
        "Use the heartbeat to proactively surface important updates, not to spam",
        "When uncertain, ask for clarification rather than guessing",
    ],
    instructions_key_principle=(
        "This assistant treats every conversation as a service interaction — "
        "be helpful, be brief, be safe. Security comes first: never leak "
        "credentials, never execute unconfirmed destructive operations, "
        "and always respect the user's privacy across platforms."
    ),
    instructions_gotchas=[
        "Channel tokens are in environment variables, never in config files",
        "Heartbeat tasks run even when the user isn't actively chatting",
        "SKILL.md files in workspace/skills/ take precedence over managed skills",
        "OpenShell sandbox blocks all outbound traffic by default — add network policies for APIs you need",
    ],

    skills=_ASSISTANT_SKILLS,

    orchestrator_pipeline="greeting → (user message) → route to skill or general response",
    orchestrator_status_flow="idle → processing → responding → idle",
    orchestrator_decision_tree=(
        "On each message:\n"
        "  |- Is greeting? → greeting skill\n"
        "  |- Is skill command (e.g. /search)? → execute named skill\n"
        "  |- Matches auto-skill context? → execute auto skill\n"
        "  \\- General message → conversational response"
    ),
    orchestrator_when_to_stop="When the user explicitly ends the conversation or goes idle for >10 minutes",

    permissions_confirm_shell=["rm *", "git push --force"],
    permissions_confirm_actions=["Send message to external channel", "Delete calendar event"],

    env_required=[
        {"name": "ANTHROPIC_API_KEY", "description": "API key for the primary LLM provider"},
    ],
    env_optional=[
        {"name": "BRAVE_API_KEY", "description": "API key for web search (Brave Search)"},
        {"name": "TELEGRAM_BOT_TOKEN", "description": "Bot token for Telegram integration"},
        {"name": "DISCORD_BOT_TOKEN", "description": "Bot token for Discord integration"},
    ],
    scaffold_learning=True,
)


DOMAIN_CONFIGS: Dict[str, DomainConfig] = {
    "ml": ML_CONFIG,
    "web": WEB_CONFIG,
    "devops": DEVOPS_CONFIG,
    "research": RESEARCH_CONFIG,
    "assistant": ASSISTANT_CONFIG,
}


def get_domain_config(domain: str, locale: str = "en") -> Optional[DomainConfig]:
    """Return domain config for the given locale, falling back to English."""
    if locale == "ja":
        try:
            from aes.i18n.domains_ja import DOMAIN_CONFIGS as JA_CONFIGS
            config = JA_CONFIGS.get(domain)
            if config:
                return config
        except ImportError:
            pass
    return DOMAIN_CONFIGS.get(domain)
