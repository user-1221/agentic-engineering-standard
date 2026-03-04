# 04 — Registries: Extensible Component Definitions

A registry is a declarative catalog of components. The key pattern: **adding a component = adding a data entry, not writing new orchestration code**. The pipeline reads the registry dynamically.

## Origin

Extracted from `config/model_registry.py` — the "brain" of the ML Model Factory. A 500-line Python dict defining 27 ML models across 7 problem types. Adding a model means adding a dict entry. Zero code changes to the pipeline.

## Location

`.agent/registry/` — one YAML file per registry.

```
.agent/registry/
  models.yaml           # Component definitions
  metrics.yaml          # Quality gates and evaluation criteria
```

## Format

```yaml
# .agent/registry/models.yaml
aes_registry: "1.0"

id: "models"
description: "ML models across 7 problem types"

# ── Entry Schema ──────────────────────────────────────────
# Documents what each entry must/can contain.
# This is documentation for the agent, not JSON Schema validation.
entry_schema:
  required:
    - name: "class"
      type: "string"
      description: "Class name to instantiate"
    - name: "module"
      type: "string"
      description: "Import path"
    - name: "handler"
      type: "string"
      description: "Which handler module processes this"
  optional:
    - name: "serialize_fmt"
      type: "string"
      description: "Native file extension (.json, .joblib, etc.)"
    - name: "capabilities"
      type: "object"
      description: "What the component can handle natively"
  dynamic:
    - name: "search_space"
      type: "object"
      description: "Hyperparameter ranges (per component)"

# ── Interface Contract ────────────────────────────────────
# Every handler for entries in this registry must implement
# these functions. This is the abstraction that makes the
# pipeline component-agnostic.
interface:
  description: "Uniform handler interface"
  functions:
    - name: "create_objective"
      signature: "(key, config, X_train, y_train, X_val, y_val) -> callable"
      description: "Return optimization objective function"
    - name: "train_final"
      signature: "(key, config, best_params, X_train, y_train) -> model"
      description: "Train on best parameters"
    - name: "save"
      signature: "(model, path) -> Path"
      description: "Serialize to native format"
    - name: "load"
      signature: "(key, config, path) -> model"
      description: "Deserialize from native format"
    - name: "evaluate"
      signature: "(model, X_test, y_test) -> dict"
      description: "Compute metrics on test set"

# ── Categories ────────────────────────────────────────────
categories:
  binary_classification:
    catboost_classifier:
      class: "CatBoostClassifier"
      module: "catboost"
      handler: "trainers.gradient_boost"
      serialize_fmt: ".cbm"
      capabilities:
        handles_categorical: true
        handles_missing: true
        needs_scaling: false
      search_space:
        iterations: { type: "int", low: 200, high: 2000 }
        depth: { type: "int", low: 4, high: 10 }
        learning_rate: { type: "float_log", low: 0.01, high: 0.3 }

    random_forest_classifier:
      class: "RandomForestClassifier"
      module: "sklearn.ensemble"
      handler: "trainers.sklearn_models"
      serialize_fmt: ".joblib"
      capabilities:
        handles_categorical: false
        handles_missing: false
        needs_scaling: false
      search_space:
        n_estimators: { type: "int", low: 100, high: 1000 }
        max_depth: { type: "int", low: 3, high: 20 }

  regression:
    catboost_regressor:
      class: "CatBoostRegressor"
      module: "catboost"
      handler: "trainers.gradient_boost"
      serialize_fmt: ".cbm"
      # ...
```

## Design Principles

### 1. Categories Group Related Components

Categories are the top-level grouping (e.g., `binary_classification`, `regression`). The pipeline selects a category, then iterates over its entries.

### 2. Entry Schema Documents the Contract

The `entry_schema` section tells agents what fields exist and what they mean. This is not for runtime validation — it's for agent understanding.

### 3. Interface Contract Defines the Abstraction

The `interface` section declares what functions every handler must implement. This is what makes the pipeline component-agnostic:

- The pipeline calls `handler.train_final(key, config, params, X, y)`
- It doesn't know if the handler uses CatBoost, XGBoost, or sklearn
- Adding a new framework = adding a handler + registry entries

### 4. Dynamic Fields Enable Per-Component Customization

Fields like `search_space` vary per entry. The pipeline reads them at runtime to configure optimization.

## Dual Representation

Registries often exist in two forms:

1. **YAML** (`.agent/registry/models.yaml`) — for agent understanding and cross-tool portability
2. **Code** (`config/model_registry.py`) — for runtime execution

These stay in sync by convention. The YAML is the documentation; the code is the implementation. For simple systems, the code can read directly from YAML. For performance-critical systems, keep both.

## Quality Gates Registry

A registry can also define evaluation criteria:

```yaml
# .agent/registry/metrics.yaml
aes_registry: "1.0"

id: "metrics"
description: "Evaluation metrics and quality gates"

categories:
  binary_classification:
    primary: "roc_auc"
    secondary: ["accuracy", "f1", "precision", "recall"]
    direction: "maximize"
    baseline: "majority_class"
    quality_gate:
      min_threshold: 0.75
      overfitting_max_gap: 0.15

  regression:
    primary: "rmse"
    secondary: ["mae", "r2", "mape"]
    direction: "minimize"
    baseline: "predict_mean"
    quality_gate:
      min_r2: 0.50
      overfitting_max_gap_relative: 0.30
```

## When to Use a Registry

Use a registry when:
- You have multiple components of the same type (models, routes, services, environments)
- Adding a new component should not require changing orchestration code
- Components share a common interface but have different implementations
- An agent needs to understand what's available and select from it

Do NOT use a registry for:
- Configuration that varies per environment (use `agent.yaml` environment section)
- One-off components with no shared interface
- Simple key-value settings (use `agent.yaml` resources section)
