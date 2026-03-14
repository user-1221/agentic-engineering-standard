"""Japanese domain configurations for aes init."""

from __future__ import annotations

from typing import Dict

from aes.domains import (
    CommandDef,
    DomainConfig,
    SkillDef,
    WorkflowDef,
    WorkflowStateDef,
    WorkflowTransitionDef,
)


# ---------------------------------------------------------------------------
# ML ドメイン設定
# ---------------------------------------------------------------------------

_ML_SKILLS = [
    SkillDef(
        id="discover",
        name="Discover Datasets",
        version="1.0.0",
        description="OpenMLとKaggle APIから新しい公開データセットを検索します。パイプラインに新しいデータが必要な場合、またはdiscoveredステータスのデータセットがない場合に使用します。複数のソースを照会し、重複を排除し、品質基準でフィルタリングします。",
        stage=1,
        phase="ingestion",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "アクティブなデータベース接続"},
        ],
        inputs_optional=[
            {"name": "max_datasets", "type": "int", "default": "50",
             "description": "1回の実行で発見する最大データセット数"},
        ],
        inputs_environment=["OPENML_APIKEY", "KAGGLE_USERNAME", "KAGGLE_KEY"],
        outputs=[
            {"name": "new_dataset_ids", "type": "list[int]",
             "description": "新しく発見されたデータセットのID"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage discover",
        error_strategy="per-item-isolation",
        code_primary="pipeline/discover.py",
        tags=["data-ingestion", "openml", "kaggle"],
        blocks=["examine"],
        negative_triggers=["手動CSVインポートやローカルファイル取り込みには使用しないでください"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "data/**"]}, "network": True},
        runbook_purpose="品質とライセンス基準を満たすOpenMLとKaggleの新しい公開データセットを検索します。",
        runbook_when="- `discovered`ステータスのデータセットがない\n- ユーザーが新しいデータソースを要求\n- 毎日のスケジュール実行",
        runbook_how="1. OpenML APIにサイズ/ライセンスフィルタに一致するデータセットを照会\n2. Kaggle APIにターゲットドメインのデータセットを照会\n3. `dataset_exists()`で既存レコードと重複排除\n4. `insert_dataset()`で新規レコードを挿入\n5. `insert_attribution()`で帰属情報を記録",
        runbook_decision_tree="各候補データセットについて:\n  |- 既に存在する? -> スキップ\n  |- ライセンスがホワイトリストにない? -> スキップ\n  |- 行数 < 100 または > 500,000? -> スキップ\n  |- 特徴量 < 3? -> スキップ\n  \\- すべてのチェックに合格? -> \"discovered\"として挿入",
        runbook_error_handling="- **APIタイムアウト**: 1回リトライ、その後ソースをスキップ\n- **レート制限**: スリープしてリトライ\n- **無効なレスポンス**: デバッグログ、データセットをスキップ",
    ),
    SkillDef(
        id="examine",
        name="Examine Dataset",
        version="1.0.0",
        description="データセットをダウンロードし、プロファイリングを行い、品質スコアを計算します。discoverが完了しデータセットがdiscoveredステータスの場合に使用します。特徴量の型を検出し、ハードリジェクションをチェックし、parquetとして保存します。",
        stage=2,
        phase="profiling",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "アクティブなデータベース接続"},
            {"name": "dataset_id", "type": "int",
             "description": "検査するデータセット"},
        ],
        outputs=[
            {"name": "quality_score", "type": "float",
             "description": "0.0-1.0の加重品質スコア"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage examine --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/examine.py",
        tags=["data-quality", "profiling"],
        depends_on=["discover"],
        negative_triggers=["既にexaminedステータス以降のデータセットには使用しないでください"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "data/**"]}, "network": True},
        runbook_purpose="データセットをダウンロードし、品質スコアを計算し、特徴量の型を検出し、学習する価値があるか判断します。",
        runbook_when="- データセットが`discovered`ステータス\n- discoverスキル完了後",
        runbook_how="1. ソースからデータをダウンロード（OpenML APIまたはKaggle）\n2. 品質スコアを計算（加重）: 欠損30%、重複15%、定数15%、不均衡20%、特徴量10%、カーディナリティ10%\n3. ハードリジェクションをチェック: >50%欠損、<3特徴量、<10少数クラスサンプル\n4. 特徴量の型を検出: 数値、カテゴリカル、日時、テキスト\n5. parquetとして保存\n6. `examined`に進む",
        runbook_decision_tree="データセットをダウンロード\n  |- ダウンロード失敗? -> リジェクト: \"download_failed\"\n  |- >50%欠損値? -> リジェクト: \"too_many_missing\"\n  |- <3特徴量? -> リジェクト: \"too_few_features\"\n  |- <10少数クラスサンプル? -> リジェクト: \"insufficient_minority\"\n  \\- 合格? -> ステータス: \"examined\"",
        runbook_error_handling="- **ネットワークエラー**: ログして続行\n- **無効なデータ**: スキップしてログ",
    ),
    SkillDef(
        id="classify",
        name="Classify Problem",
        version="1.0.0",
        description="問題タイプを検出し、レジストリから候補モデルを選択します。examineの後、データセットがexaminedステータスでquality_score >= 0.30の場合に使用します。二値分類、多クラス分類、回帰、時系列、異常検知、クラスタリングに対応。",
        stage=3,
        phase="classification",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "アクティブなデータベース接続"},
            {"name": "dataset_id", "type": "int",
             "description": "分類するデータセット"},
        ],
        outputs=[
            {"name": "problem_type", "type": "str",
             "description": "検出された問題タイプ（binary, multiclass, regressionなど）"},
            {"name": "selected_models", "type": "list[str]",
             "description": "レジストリから選択されたモデルキー"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage classify --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/classify.py",
        tags=["classification", "model-selection"],
        depends_on=["examine"],
        blocks=["train"],
        negative_triggers=["品質閾値未満のデータセット（quality_score < 0.30）には使用しないでください"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**"]}, "network": False},
        runbook_purpose="問題タイプ（二値分類、多クラス分類、回帰、時系列、異常検知、クラスタリング）を検出し、モデルレジストリから候補モデルを選択します。",
        runbook_when="- データセットが`examined`ステータス\n- examineスキル完了後、quality_score >= 0.30",
        runbook_how="1. examineステージからデータセットプロファイルをロード\n2. ターゲット列を分析: カーディナリティ、分布、dtype\n3. ヒューリスティクスで問題タイプを検出\n4. model_registryから互換モデルを照会\n5. データセットサイズと特徴量タイプでモデルをフィルタ\n6. 選択モデルを保存し`classified`に進む",
        runbook_decision_tree="ターゲット列を分析:\n  |- 数値 + 高カーディナリティ? -> 回帰\n  |- カテゴリカル + 2クラス? -> 二値分類\n  |- カテゴリカル + 3+クラス? -> 多クラス分類\n  |- 日時ターゲット? -> 時系列\n  |- ターゲット列なし? -> クラスタリングまたは異常検知\n  \\- 曖昧? -> デフォルトで多クラス分類",
        runbook_error_handling="- **曖昧なターゲット**: デフォルトで多クラス、警告ログ\n- **互換モデルなし**: 理由付きでデータセットをリジェクト",
    ),
    SkillDef(
        id="train",
        name="Train Models",
        version="1.0.0",
        description="Optuna HPOを実行し、データセットのすべての候補モデルを学習します。classifyの後、データセットがclassifiedステータスでリソース制限を満たしている場合に使用します。各モデルをper-item isolationで独立して学習します。",
        stage=4,
        phase="training",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "アクティブなデータベース接続"},
            {"name": "dataset_id", "type": "int",
             "description": "学習するデータセット"},
        ],
        inputs_optional=[
            {"name": "model_keys", "type": "list[str]",
             "description": "学習する特定のモデル（デフォルト: すべての選択済み）"},
        ],
        inputs_environment=["OPTUNA_TIMEOUT", "OPTUNA_N_TRIALS"],
        outputs=[
            {"name": "experiment_ids", "type": "list[int]",
             "description": "完了した実験のID"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage train --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/train.py",
        tags=["training", "optuna", "hpo"],
        depends_on=["classify"],
        blocks=["evaluate"],
        negative_triggers=["CPU > 70%またはメモリ > 75%の場合は使用しないでください", "未分類のデータセットには使用しないでください"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "models/**", "data/**"]}, "network": False},
        runbook_purpose="Optunaハイパーパラメータ最適化を実行し、データセットのすべての候補モデルを学習します。",
        runbook_when="- データセットが`classified`ステータス\n- リソース制限を満たしている（CPU <70%、メモリ <75%）",
        runbook_how="各選択モデルについて:\n1. データを前処理（フレームワーク対応）\n2. Optuna HPOを実行（TPESampler, MedianPruner）\n3. 最適パラメータで最終モデルを学習\n4. テストセットで評価\n5. ネイティブ形式でモデルを保存\n6. MLflowとSQLiteにログ",
        runbook_decision_tree="各model_keyについて:\n  |- 前処理失敗? -> 実験を失敗にマーク、続行\n  |- Optunaが良い試行を見つけない? -> 失敗にマーク、続行\n  |- 学習がクラッシュ? -> error_messageで失敗にマーク、続行\n  \\- 成功? -> モデルを保存、メトリクスをログ、完了にマーク\n\nすべてのモデル後:\n  |- 少なくとも1つ完了? -> ステータス: \"trained\"\n  \\- すべて失敗? -> ステータス: \"rejected\"",
        runbook_error_handling="- 各モデルは独立して学習（per-item-isolation）\n- 1つのモデルの失敗が他に影響しない\n- エラーメッセージはexperiment.error_messageに保存",
    ),
    SkillDef(
        id="evaluate",
        name="Evaluate Models",
        version="1.0.0",
        description="学習済みモデルを比較し、過学習をチェックし、品質ゲートを適用します。trainの後、データセットがtrainedステータスで少なくとも1つの完了した実験がある場合に使用します。",
        stage=5,
        phase="evaluation",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "アクティブなデータベース接続"},
            {"name": "dataset_id", "type": "int",
             "description": "評価するデータセット"},
        ],
        inputs_optional=[
            {"name": "quality_gates", "type": "dict",
             "description": "カスタム品質ゲート閾値（デフォルト: 設定から）"},
        ],
        outputs=[
            {"name": "best_experiment_id", "type": "int",
             "description": "最高性能の実験ID"},
            {"name": "passes_quality_gates", "type": "bool",
             "description": "最良モデルが品質基準を満たすか"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage evaluate --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/evaluate.py",
        tags=["evaluation", "quality-gates", "model-comparison"],
        depends_on=["train"],
        blocks=["package"],
        negative_triggers=["完了した実験がない場合は使用しないでください"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**"]}, "network": False},
        runbook_purpose="すべての学習済みモデルを比較し、過学習を検出し、品質ゲートをチェックし、最良の実験を選択します。",
        runbook_when="- データセットが`trained`ステータス\n- 少なくとも1つの実験が正常に完了",
        runbook_how="1. データセットの完了した実験をすべてロード\n2. 主要メトリクスでランキング（accuracy, RMSEなど）\n3. 過学習チェック: train-valギャップ > 0.15は警告\n4. 品質ゲートチェック: 最小メトリクス閾値\n5. ベースラインチェック: ランダム/多数決を上回る必要\n6. 最良の実験を選択し`evaluated`に進む",
        runbook_decision_tree="各完了した実験について:\n  |- Train-valギャップ > 0.15? -> 過学習警告をフラグ\n  |- 品質ゲート未満? -> 不合格にマーク\n  |- ベースラインより悪い? -> 不合格にマーク\n  \\- すべてのチェックに合格? -> 最良候補\n\nランキング後:\n  |- 少なくとも1つ合格? -> 最良を選択、パッケージング準備完了\n  \\- すべて不合格? -> 再フレーミングを検討（classifyに戻る）",
        runbook_error_handling="- **実験なし**: 評価不可、trainedステータスを維持\n- **すべて過学習**: 警告ログ、品質ゲートを超えていれば最良を選択",
    ),
    SkillDef(
        id="package",
        name="Package Model",
        version="1.0.0",
        description="最良モデルをネイティブ形式でエクスポートし、デプロイ用zipバンドルを作成します。evaluateがpasses_quality_gates=trueを確認した後に使用します。",
        stage=6,
        phase="packaging",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "アクティブなデータベース接続"},
            {"name": "dataset_id", "type": "int",
             "description": "最良モデルをパッケージングするデータセット"},
        ],
        outputs=[
            {"name": "package_path", "type": "str",
             "description": "作成されたzipバンドルのパス"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage package --dataset-id {ID}",
        error_strategy="fail-fast",
        code_primary="pipeline/package.py",
        tags=["packaging", "serialization", "deployment"],
        depends_on=["evaluate"],
        blocks=["publish"],
        negative_triggers=["最良モデルが品質ゲートに不合格の場合は使用しないでください"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**", "models/**", "packages/**"]}, "network": False},
        runbook_purpose="最良モデルをネイティブシリアライゼーション形式でエクスポートし、デプロイ用zipにバンドルします。",
        runbook_when="- データセットに品質ゲートを通過した最良実験がある\n- evaluateスキルがpasses_quality_gates=trueを確認後",
        runbook_how="1. 最良実験とその学習済みモデルをロード\n2. ネイティブ形式でエクスポート（CatBoost .cbm, XGBoost .json, LightGBM .txt, sklearn .joblib）\n3. メトリクスとメタデータ付きモデルカードを生成\n4. zipバンドルを作成: モデルファイル + モデルカード + 設定\n5. バンドルの整合性を検証\n6. `packaged`に進む",
        runbook_decision_tree="最良実験をロード:\n  |- モデルファイルが存在? -> ネイティブ形式でエクスポート\n  |   |- CatBoost? -> .cbm形式\n  |   |- XGBoost? -> .json形式\n  |   |- LightGBM? -> .txt形式\n  |   \\- sklearn? -> .joblib形式\n  |- モデルファイルが見つからない? -> 中止、再学習が必要\n  \\- バンドル作成完了? -> チェックサム検証、ステータス進行",
        runbook_error_handling="- **モデルファイルが見つからない**: 中止、データセットはtrainedに留まる\n- **シリアライゼーションエラー**: エラーログ、代替形式を試行\n- **zip作成失敗**: 1回リトライ、その後中止",
    ),
    SkillDef(
        id="publish",
        name="Publish Model",
        version="1.0.0",
        description="モデルをHuggingFace Hubにアップロードし、予測APIに登録します。検証済みzipバンドルが存在するpackageの後に使用します。HF_TOKEN環境変数が必要です。",
        stage=7,
        phase="distribution",
        inputs_required=[
            {"name": "db_connection", "type": "sqlite3.Connection",
             "description": "アクティブなデータベース接続"},
            {"name": "dataset_id", "type": "int",
             "description": "パッケージ済みモデルを公開するデータセット"},
        ],
        inputs_environment=["HF_TOKEN"],
        outputs=[
            {"name": "published_urls", "type": "list[str]",
             "description": "モデルが利用可能になったURL"},
        ],
        trigger_command="python scripts/run_pipeline.py --stage publish --dataset-id {ID}",
        error_strategy="per-item-isolation",
        code_primary="pipeline/publish.py",
        tags=["publishing", "huggingface", "api-registration"],
        depends_on=["package"],
        negative_triggers=["HF_TOKENが設定されていない場合は使用しないでください", "未パッケージのモデルには使用しないでください"],
        allowed_tools={"shell": True, "files": {"read": True, "write": ["pipeline/**"]}, "network": True},
        runbook_purpose="パッケージ済みモデルをHuggingFace Hubにアップロードし、従量課金制予測APIに登録します。",
        runbook_when="- データセットが`packaged`ステータス\n- パッケージzipが存在し検証済み\n- HF_TOKEN環境変数が設定済み",
        runbook_how="1. packageステージからパッケージzipをロード\n2. モデルカード付きでHuggingFace Hubにアップロード\n3. 予測APIエンドポイントにモデルを登録\n4. 従量課金アクセス用APIキーを生成\n5. 両プラットフォームの応答を確認\n6. `published`に進む",
        runbook_decision_tree="プラットフォームに公開:\n  |- HuggingFaceアップロード\n  |   |- 成功? -> URLを記録\n  |   \\- 失敗? -> エラーログ、APIに続行\n  |- API登録\n  |   |- 成功? -> エンドポイントURLを記録\n  |   \\- 失敗? -> エラーログ\n  \\- 少なくとも1つ成功? -> ステータス: published\n     \\- 両方失敗? -> packagedに留まる、エラーログ",
        runbook_error_handling="- **HF_TOKENが無効**: HFアップロード中止、APIのみ試行\n- **ネットワークエラー**: プラットフォームごとに1回リトライ\n- **API登録失敗**: ログしてpackagedステータスを維持",
    ),
]

_ML_WORKFLOW = WorkflowDef(
    id="dataset-pipeline",
    entity="dataset",
    description="発見から公開までのデータセットライフサイクル",
    states=[
        WorkflowStateDef("discovered", "データベースに検出・登録済み", initial=True),
        WorkflowStateDef("examined", "ダウンロード、プロファイリング、品質スコア算出済み"),
        WorkflowStateDef("classified", "問題タイプ検出、モデル選択済み"),
        WorkflowStateDef("training", "モデル学習中", active=True),
        WorkflowStateDef("trained", "全モデル学習完了、評価待ち"),
        WorkflowStateDef("packaged", "最良モデルをzipにパッケージ済み"),
        WorkflowStateDef("published", "APIとHuggingFaceで公開中", terminal=True),
        WorkflowStateDef("rejected", "品質基準に不合格", terminal=True),
    ],
    transitions=[
        WorkflowTransitionDef("discovered", "examined", skill="examine",
                              conditions=["データファイルがダウンロード可能"], on_failure="rejected"),
        WorkflowTransitionDef("examined", "classified", skill="classify",
                              conditions=["quality_score >= 0.30"], on_failure="rejected"),
        WorkflowTransitionDef("classified", "training", skill="train",
                              conditions=["少なくとも1つのモデルが選択済み", "リソース制限を満たしている"]),
        WorkflowTransitionDef("training", "trained", skill="train",
                              conditions=["少なくとも1つの実験が完了"],
                              on_failure="rejected"),
        WorkflowTransitionDef("trained", "packaged", skill="package",
                              conditions=["最良実験が品質ゲートに合格",
                                          "最良実験がベースラインを上回る"],
                              on_failure="rejected"),
        WorkflowTransitionDef("packaged", "published", skill="publish",
                              conditions=["少なくとも1つのプラットフォームで成功"]),
        WorkflowTransitionDef("trained", "classified", skill="classify",
                              conditions=["すべてのモデルが品質ゲート未満"],
                              description="すべてのモデルが失敗した場合に問題タイプを再フレーミング"),
    ],
)

ML_CONFIG = DomainConfig(
    mode="agent-integrated",
    workflow_commands=[
        CommandDef(
            id="build",
            trigger="/build",
            description="MLパイプラインのコードベースをゼロから構築: プロジェクト構成、データベース、パイプラインステージ、モデルレジストリ、設定、スクリプト、テスト",
            runbook_purpose="完全なMLパイプラインコードベースを構築します。エージェントはプロジェクト構成を作成し、データベースをセットアップし、各パイプラインステージを実装し、モデルレジストリを構築し、設定を記述し、CLIスクリプトを追加し、テストで検証します。",
            worker_specialty="MLパイプラインコードベースの構築 — モジュール、データベース、ステージ、レジストリ",
            runbook_phases=[
                {"title": "プロジェクト構成", "content": "ディレクトリレイアウトを作成: pipeline/, trainers/, config/, serving/, scripts/, tests/。pyproject.toml、__init__.pyファイル、仮想環境をセットアップ。"},
                {"title": "データベースとストレージ", "content": "データセット、モデル、実行用のSQLiteスキーマを実装。マイグレーションスクリプトとヘルパー関数（insert, update, query）を作成。"},
                {"title": "パイプラインステージ", "content": "各ステージモジュールを構築: discover.py, examine.py, classify.py, train.py, evaluate.py, package.py, publish.py。各モジュールはDBから読み込み、処理し、結果を書き戻す。"},
                {"title": "モデルレジストリ", "content": "config/model_registry.py を作成 — これがブレイン。モデルエントリ（名前、クラス、探索空間、メトリクス）を定義。モデルの追加 = dict エントリの追加。"},
                {"title": "設定", "content": "環境変数ベースの設定でconfig/settings.pyを作成。品質ゲート、閾値、リソース制限、APIエンドポイントを定義。"},
                {"title": "スクリプトとCLI", "content": "--stageと--dataset-idフラグ付きのscripts/run_pipeline.pyを構築。一般的な操作用の便利スクリプトを追加。"},
                {"title": "テストと検証", "content": "各パイプラインステージのユニットテストを記述。小さなデータセットでdiscover->examine->classifyを実行する統合テストを追加。すべてのインポートとCLIコマンドが動作することを確認。"},
            ],
        ),
        CommandDef(
            id="train",
            trigger="/train",
            description="完全なMLパイプラインを実行: discover, examine, classify, train, evaluate, package, publish",
            runbook_purpose="完全なMLパイプラインをエンドツーエンドで実行します。エージェントはデータセットを発見し、プロファイリングし、Optuna HPOでモデルを学習し、結果を評価し、合格したものを公開します。",
            worker_specialty="MLトレーニングパイプラインの実行 — HPO、評価、パッケージング",
            runbook_phases=[
                {"title": "Discover", "content": "品質とライセンス基準に合致するOpenML/Kaggle APIから新しいデータセットを検索。"},
                {"title": "Examine", "content": "ダウンロード、プロファイリング、品質スコアの算出。閾値未満のデータセットをリジェクト。"},
                {"title": "Classify", "content": "問題タイプを検出し、レジストリから候補モデルを選択。"},
                {"title": "Train", "content": "各候補モデルにOptuna HPOを実行。最適パラメータで最終モデルを学習。"},
                {"title": "Evaluate", "content": "品質ゲートに対してモデルをスコアリング。ベースラインと比較。"},
                {"title": "Package", "content": "モデルのシリアライゼーション、モデルカードの生成、アーティファクトの準備。"},
                {"title": "Publish", "content": "合格モデルを完全なメタデータ付きでHuggingFace Hubにプッシュ。"},
            ],
        ),
    ],
    instructions_description="データセットの発見、モデルの学習、品質評価、合格者のパッケージング、予測提供を行う自動MLパイプライン。",
    instructions_quick_ref="<!-- エージェント: scripts/、Makefile、またはpyproject.tomlからコマンドを抽出してください。パイプラインの実行、学習、テストのための3-5個の最も一般的なコマンドを表示。 -->",
    instructions_project_structure="<!-- エージェント: ディレクトリ一覧を取得し、主要ディレクトリに注釈してください。典型的なMLパイプライン構成: パイプラインステージ、モデルトレーナー、設定、サービング層、スクリプト、テスト。 -->",
    instructions_rules=[
        "**モデルレジストリがブレイン** -- モデルの追加は設定エントリの追加であり、新しい学習コードを書くことではない。",
        "**リソース制限** -- 学習中はCPUとメモリを監視。制限を超えた場合は作業をスキップまたはキューイング。",
        "**グレースフルフェイル** -- 各データセット/モデルはエラー処理でラップ。エラーをログし、次のアイテムに続行。",
    ],
    instructions_workflow_phases=[
        {"title": "データの検索", "content": "データソースを検索するか、ユーザー提供のデータセットを取り込む。"},
        {"title": "パイプラインの実行", "content": "discover -> examine -> classify -> train -> evaluateステージを実行。"},
        {"title": "結果の分析（スキップ禁止）", "content": "確認事項: 過学習（train-valギャップが大きすぎる）、未学習（品質ゲート未満）、全モデル失敗、ベースライン未達、問題タイプの不一致。"},
        {"title": "イテレーション", "content": "優先順のレバー: ハイパーパラメータチューニング（試行数/時間の増加）→ モデル選択（探索空間）→ 問題の再フレーミング → 前処理の変更 → 品質ゲートの調整。"},
        {"title": "パッケージングと公開", "content": "品質が確認された後のみ。evaluate -> package -> publish。"},
    ],
    instructions_key_principle="エージェントの仕事はコマンドを実行するだけではありません。理解し、分析し、イテレーションし、品質を提供することです。",
    instructions_gotchas=[],
    skills=_ML_SKILLS,
    orchestrator_pipeline="discover -> examine -> classify -> train -> evaluate -> package -> publish",
    orchestrator_status_flow="discovered -> examined -> classified -> training -> trained -> packaged -> published\n    |            |                                 |\n    v            v                                 v\n rejected     rejected                          rejected",
    orchestrator_decision_tree="まず: パイプラインが既に完了しているか確認（すべてのアイテムが終了ステータス）。\n  完了している場合 -> ステータスサマリーを報告し、ユーザーに確認: 再実行 / 新規セッション / 再検証 / 終了。\n  未完了の場合 -> 続行:\n\n各ステージ [discover, examine, classify, train, evaluate, package, publish] について:\n  1. リソース制限を確認（CPU <70%、メモリ <75%）\n  2. 現在のステータスのデータセットを取得（--dataset-idの場合は単一）\n  3. 各データセットについて:\n     a. ステージ関数を実行\n     b. 成功時: ステータスを次のステージに進める\n     c. 失敗時: エラーログ、回復不能ならリジェクト\n  4. 報告: N件処理、N件失敗、N件スキップ\n\n特別: trainステージ後、evaluateの前に分析を実行:\n  - 過学習チェック（train-valギャップ >0.15）\n  - 未学習チェック（すべてが品質ゲート未満）\n  - ベースラインチェック（ランダムより良い?）\n  - すべて失敗の場合: 再フレーミングを検討（trained -> classified）",
    orchestrator_when_to_stop="- すべてのデータセットが終了ステータス（publishedまたはrejected）\n- リソース制限超過\n- ユーザーが停止を要求\n- 処理するデータセットがない",
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
        {"name": "OPENML_APIKEY", "description": "OpenML APIキー（データセット発見用）"},
        {"name": "HF_TOKEN", "description": "HuggingFaceトークン（モデル公開用）"},
    ],
    env_optional=[
        {"name": "OPTUNA_TIMEOUT", "default": "300", "description": "モデルあたりのHPO秒数"},
        {"name": "OPTUNA_N_TRIALS", "default": "50", "description": "モデルあたりの最大試行数"},
    ],
)


# ---------------------------------------------------------------------------
# Web ドメイン設定
# ---------------------------------------------------------------------------

WEB_CONFIG = DomainConfig(
    mode="dev-assist",
    workflow_commands=[
        CommandDef(
            id="build",
            trigger="/build",
            description="フィーチャーをエンドツーエンドで構築: スキャフォールド、実装、テスト、レビュー、デプロイ",
            runbook_purpose="フィーチャー開発の完全なライフサイクルをガイドします。エージェントはボイラープレートをスキャフォールドし、フィーチャーを実装し、テストを実行し、コード品質をレビューし、デプロイします。",
            worker_specialty="Webフィーチャーのエンドツーエンド構築 — スキャフォールド、実装、テスト、デプロイ",
            runbook_phases=[
                {"title": "スキャフォールド", "content": "フィーチャー用のマイグレーション、ルート、コンポーネント、テストスタブを生成。"},
                {"title": "実装", "content": "マイグレーションロジック、APIルート、UIコンポーネントを記述し、フィーチャーフラグを接続。"},
                {"title": "テスト", "content": "ユニット、統合、e2eテストスイートを実行。先に進む前に失敗を修正。"},
                {"title": "レビュー", "content": "リント、型チェック、バンドル分析、セキュリティスキャンを実行。"},
                {"title": "デプロイ", "content": "ステージングにデプロイし、ヘルスチェックを確認後、本番に昇格。"},
            ],
        ),
    ],
    instructions_description="認証、課金、リアルタイム更新を備えたフルスタックWebアプリケーション。",
    instructions_quick_ref="<!-- エージェント: package.json scripts、Makefile、または同等のものからコマンドを抽出してください。開発サーバー、テスト、マイグレーション、デプロイのための3-5個の最も一般的なコマンドを表示。 -->",
    instructions_project_structure="<!-- エージェント: ディレクトリ一覧を取得し、主要ディレクトリに注釈してください。典型的なWebアプリ構成: ページ/ルート、コンポーネント、API層、データベース/ORM、認証、課金、テスト。 -->",
    instructions_rules=[
        "**すべてのAPIルートに認証** -- 認証ミドルウェアを一貫して使用。保護されていないエンドポイントは不可。",
        "**フィーチャーフラグ** -- 安定するまで新機能はフィーチャーフラグの後ろに配置。",
    ],
    instructions_workflow_phases=[
        {"title": "要件の理解", "content": "フィーチャーは何をする？どのデータが必要？既存のフィーチャーとどう連携する？"},
        {"title": "実装", "content": "スキーママイグレーション -> APIルート -> UIコンポーネント -> テスト。"},
        {"title": "テスト（スキップ禁止）", "content": "ユニットテスト合格、統合テスト合格、ステージングでの手動QA。"},
        {"title": "デプロイ", "content": "まずステージング、メトリクスを確認してから本番。"},
    ],
    instructions_key_principle="インクリメンタルにリリース。すべてのフィーチャーには本番に行く前にマイグレーション、テスト、フィーチャーフラグが必要。",
    instructions_gotchas=[],
    skills=[],  # Web skills omitted for brevity — fall back to English
    orchestrator_pipeline="scaffold -> implement -> test -> review -> deploy",
    orchestrator_status_flow="planned -> in_progress -> testing -> staging -> deployed\n                                                 /\n                                          blocked（任意のステージ）",
    orchestrator_decision_tree="まず: パイプラインが既に完了しているか確認（すべてのアイテムが終了ステータス）。\n  完了している場合 -> ステータスサマリーを報告し、ユーザーに確認: 再実行 / 新規セッション / 再検証 / 終了。\n  未完了の場合 -> 続行:\n\n1. フィーチャー要件を理解\n2. スキーマ変更が必要ならマイグレーションを作成\n3. 認証ミドルウェア付きAPIルートを実装\n4. UIコンポーネントを実装（サーバーファースト、インタラクティブ時はクライアント）\n5. テストを記述（ユニット + 統合 + e2e）\n6. ステージングにデプロイ\n7. ステージングで検証（手動 + 自動チェック）\n8. フィーチャーフラグの後ろで本番にデプロイ\n9. メトリクスを監視し、安定後フラグを削除",
    orchestrator_when_to_stop="- フィーチャーがデプロイされ本番で安定\n- 検証後にフィーチャーフラグを削除\n- メインブランチですべてのテストが合格",
    workflow=None,
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
        {"name": "DATABASE_URL", "description": "PostgreSQL接続文字列"},
        {"name": "STRIPE_SECRET_KEY", "description": "課金用Stripe APIキー"},
    ],
    env_optional=[
        {"name": "NODE_ENV", "default": "development", "description": "ランタイム環境"},
    ],
)


# ---------------------------------------------------------------------------
# DevOps ドメイン設定
# ---------------------------------------------------------------------------

DEVOPS_CONFIG = DomainConfig(
    mode="dev-assist",
    workflow_commands=[
        CommandDef(
            id="provision",
            trigger="/provision",
            description="インフラストラクチャのプロビジョニングとデプロイ: provision, configure, deploy",
            runbook_purpose="インフラストラクチャのプロビジョニングとデプロイの完全なライフサイクルをガイドします。エージェントはTerraformでリソースをプロビジョニングし、Ansibleでサービスを設定し、ブルーグリーン戦略でデプロイします。",
            worker_specialty="インフラストラクチャのプロビジョニングとデプロイ — Terraform、Ansible、ブルーグリーンデプロイ",
            runbook_phases=[
                {"title": "プロビジョニング", "content": "terraform planを実行し、破壊的変更をレビューしてからapply。"},
                {"title": "設定", "content": "まずドライラン検証してからAnsible Playbookを適用。"},
                {"title": "デプロイ", "content": "ヘルスチェック付きブルーグリーンデプロイ。5分間監視。劣化した場合はロールバック。"},
            ],
        ),
    ],
    instructions_description="インフラストラクチャ自動化 — プロビジョニング、設定、デプロイ、監視、ロールバック。",
    instructions_quick_ref="<!-- エージェント: scripts/、Makefile、またはCI設定からコマンドを抽出してください。plan、apply、デプロイ、ロールバックのための3-5個の最も一般的なコマンドを表示。 -->",
    instructions_project_structure="<!-- エージェント: ディレクトリ一覧を取得し、主要ディレクトリに注釈してください。典型的なインフラ構成: IaC定義、構成管理、デプロイスクリプト、監視、コンテナ定義。 -->",
    instructions_rules=[
        "**プレビューなしで適用しない** -- インフラ変更は適用前に必ずプレビュー。",
        "**まずステージング** -- すべての変更は本番前にステージングで実施。",
        "**ロールバック準備** -- すべてのデプロイにテスト済みロールバックパスが必要。",
        "**ハードコードされたシークレット禁止** -- シークレットマネージャーを使用。認証情報をコミットしない。",
        "**すべてにタグ付け** -- すべてのリソースにservice、environment、ownerタグを付与。",
    ],
    instructions_workflow_phases=[
        {"title": "前提条件の確認", "content": "確認: イメージビルド済み、テスト合格、ステージング正常、ロールバックテスト済み。"},
        {"title": "ステージングにデプロイ", "content": "ブルーグリーンデプロイ、ヘルスチェック、スモークテスト。"},
        {"title": "監視（スキップ禁止）", "content": "エラー率、レイテンシp99、CPU/メモリを5分間監視。"},
        {"title": "昇格またはロールバック", "content": "メトリクスが安定 -> 本番に昇格。メトリクスが劣化 -> 即座にロールバック。"},
    ],
    instructions_key_principle="インフラの変更は永続的で可視的です。二度測って一度切る。常にロールバック計画を持つ。",
    instructions_gotchas=[],
    skills=[],  # DevOps skills omitted — fall back to English
    orchestrator_pipeline="provision -> configure -> deploy -> monitor -> verify",
    orchestrator_status_flow="planned -> provisioning -> configured -> deploying -> deployed -> monitored\n                                          |            |\n                                       failed      degraded -> rollback -> deployed",
    orchestrator_decision_tree="まず: パイプラインが既に完了しているか確認（すべてのアイテムが終了ステータス）。\n  完了している場合 -> ステータスサマリーを報告し、ユーザーに確認: 再実行 / 新規セッション / 再検証 / 終了。\n  未完了の場合 -> 続行:\n\n1. インフラをプロビジョニング（Terraform）\n   |- planが破壊的変更を表示? -> 停止、ユーザーに確認\n   \\- planが追加のみ? -> 適用\n2. サービスを設定（Ansible）\n   |- ドライランが予期しない変更を表示? -> 停止、調査\n   \\- ドライランが正常? -> 適用\n3. サービスをデプロイ（ブルーグリーン）\n   |- ヘルスチェック失敗? -> 即座にロールバック\n   |- エラー率 > 1%? -> 即座にロールバック\n   \\- すべて正常? -> デプロイ済みにマーク\n4. 5分間監視\n   |- メトリクスが劣化? -> ロールバック\n   \\- 安定? -> デプロイを確認",
    orchestrator_when_to_stop="- サービスがデプロイされメトリクスが安定\n- ロールバックが正常に完了\n- エスカレーションが必要（人間の介入が必要）",
    workflow=None,
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
        {"name": "AWS_PROFILE", "description": "AWS認証プロファイル"},
        {"name": "DEPLOY_ENV", "description": "ターゲット環境（staging/production）"},
    ],
    env_optional=[
        {"name": "ROLLBACK_WINDOW", "default": "300", "description": "デプロイ確認前の監視秒数"},
    ],
)


# ---------------------------------------------------------------------------
# Research ドメイン設定
# ---------------------------------------------------------------------------

RESEARCH_CONFIG = DomainConfig(
    mode="agent-integrated",
    workflow_commands=[
        CommandDef(
            id="build",
            trigger="/build",
            description="研究パイプラインのコードベースをゼロから構築: プロジェクト構成、ソースアダプター、ストレージ、パイプラインステージ、タクソノミー、スクリプト、テスト",
            runbook_purpose="完全な研究コンテンツパイプラインのコードベースを構築します。エージェントはプロジェクト構成を作成し、ソースアダプターを実装し、ストレージをセットアップし、各パイプラインステージを構築し、トピックタクソノミーを定義し、CLIスクリプトを追加し、テストで検証します。",
            worker_specialty="研究パイプラインコードベースの構築 — ソース、ストレージ、ステージ、タクソノミー",
            runbook_phases=[
                {"title": "プロジェクト構成", "content": "ディレクトリレイアウトを作成: pipeline/, sources/, config/, output/, data/, scripts/, tests/。pyproject.toml、__init__.pyファイル、仮想環境をセットアップ。"},
                {"title": "ソースアダプター", "content": "ソースアダプターを実装: arxiv.py, semantic_scholar.py, rss.py, web.py。各アダプターは認証、レート制限を処理し、正規化されたコンテンツオブジェクトを返す。"},
                {"title": "ストレージ層", "content": "生データと処理済みコンテンツ用にSQLiteまたはファイルベースのストレージをセットアップ。アイテム、メタデータ、引用、トピック割り当てのスキーマを作成。ヘルパー関数を追加。"},
                {"title": "パイプラインステージ", "content": "各ステージモジュールを構築: ingest.py, parse.py, analyze.py, organize.py, display.py。各モジュールは現在のステータスのアイテムを読み込み、処理し、ステータスを進める。"},
                {"title": "トピックタクソノミー", "content": "config/topic_taxonomy.py を作成 — 分類階層。トップレベルカテゴリ、サブカテゴリ、キーワードマッピングを定義。タクソノミーはコンテンツ処理に応じて進化。"},
                {"title": "スクリプトとCLI", "content": "--stageと--sourcesフラグ付きのscripts/pipeline.pyを構築。一般的な操作（検索、レポート生成）用の便利スクリプトを追加。"},
                {"title": "テストと検証", "content": "各パイプラインステージとソースアダプターのユニットテストを記述。サンプルコンテンツでingest->parse->analyzeを実行する統合テストを追加。すべてのインポートとCLIコマンドが動作することを確認。"},
            ],
        ),
        CommandDef(
            id="process",
            trigger="/process",
            description="コンテンツパイプラインを実行: ingest, parse, analyze, organize, display",
            runbook_purpose="完全なコンテンツ処理パイプラインを実行します。エージェントはソースからコンテンツを取り込み、構造を抽出し、知見を分析し、タクソノミーに整理し、出力を生成します。",
            worker_specialty="パイプラインを通じた研究コンテンツの処理 — 取り込み、分析、整理",
            runbook_phases=[
                {"title": "Ingest", "content": "設定されたソース（arXiv、Semantic Scholar、RSS、Web）から論文/記事を収集。"},
                {"title": "Parse", "content": "生コンテンツから構造、メタデータ、セクション、引用を抽出。"},
                {"title": "Analyze", "content": "トピックの分類、主要な知見の抽出、関連性スコアの計算。"},
                {"title": "Organize", "content": "トピック別に分類、タクソノミーの構築、関連アイテムの相互参照。"},
                {"title": "Display", "content": "処理済みコンテンツのレポート、サマリー、可視化を生成。"},
            ],
        ),
    ],
    instructions_description="研究コンテンツ処理パイプライン。論文と記事を取り込み、構造とメタデータを抽出し、知見を分析し、トピックタクソノミーで整理し、レポートを生成します。",
    instructions_quick_ref="<!-- エージェント: scripts/、Makefile、またはpyproject.tomlからコマンドを抽出してください。パイプラインの実行、ソースの取り込み、出力生成のための3-5個の最も一般的なコマンドを表示。 -->",
    instructions_project_structure="<!-- エージェント: ディレクトリ一覧を取得し、主要ディレクトリに注釈してください。典型的な研究パイプライン構成: パイプラインステージ、ソースアダプター、設定、出力、データストレージ。 -->",
    instructions_rules=[
        "**ソースの帰属** -- 取り込んだすべてのアイテムに出所とアクセス日を常に記録。",
        "**重複排除** -- 取り込み前に識別子、URL、タイトル類似度でチェック。",
        "**関連性フィルタリング** -- 設定された関連性閾値未満のアイテムをリジェクト。",
        "**インクリメンタル処理** -- 最後に完了したステージから再開、完了済みアイテムを再処理しない。",
        "**構造化出力** -- すべての分析結果を構造化形式で保存、散文だけではなく。",
    ],
    instructions_workflow_phases=[
        {"title": "ソースの取り込み", "content": "トピックフィルタに一致する新しいコンテンツを設定されたソースから照会。"},
        {"title": "構造の抽出", "content": "コンテンツを構造化されたセクション、メタデータ、引用にパース。"},
        {"title": "分析と分類", "content": "トピック分類、主要知見の抽出、関連性スコアリング。"},
        {"title": "整理と接続", "content": "タクソノミーの構築、相互参照、知識グラフの更新。"},
        {"title": "出力の生成", "content": "要求された形式でレポート、サマリー、ダッシュボードを生成。"},
    ],
    instructions_key_principle="コンテンツは原材料、構造化された知識が製品です。すべてのアイテムは生の取り込みから整理済み・相互参照済みの出力までパイプラインを通過します。",
    instructions_gotchas=[],
    skills=[],  # Research skills omitted — fall back to English
    orchestrator_pipeline="ingest -> parse -> analyze -> organize -> display",
    orchestrator_status_flow="ingested -> parsed -> analyzed -> organized -> displayed\n    |                  |\n    v                  v\n rejected           rejected",
    orchestrator_decision_tree="まず: パイプラインが既に完了しているか確認（すべてのアイテムが終了ステータス）。\n  完了している場合 -> ステータスサマリーを報告し、ユーザーに確認: 再実行 / 新規セッション / 再検証 / 終了。\n  未完了の場合 -> 続行:\n\n各ステージ [ingest, parse, analyze, organize, display] について:\n  1. 現在のステータスのアイテムを取得\n  2. 各アイテムについて:\n     a. ステージスキルを実行\n     b. 成功時: ステータスを進める\n     c. 失敗時: エラーログ、回復不能ならリジェクト\n  3. 報告: N件処理、N件リジェクト、N件スキップ\n\nanalyzeステージ後:\n  - 関連性スコアを確認\n  - 閾値未満のアイテムをリジェクト\n  - 既存の知見と矛盾するアイテムにフラグ",
    orchestrator_when_to_stop="- すべてのアイテムが終了ステータス（displayedまたはrejected）\n- ソースからの新しいアイテムがない\n- ユーザーが停止を要求",
    workflow=None,
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
        {"name": "SEMANTIC_SCHOLAR_API_KEY", "default": "", "description": "Semantic Scholar APIキー（オプション、レート制限が緩和されます）"},
        {"name": "MAX_ITEMS_PER_RUN", "default": "50", "description": "パイプライン実行あたりの最大処理アイテム数"},
    ],
)


# ---------------------------------------------------------------------------
# ベース設定
# ---------------------------------------------------------------------------

_BUILD_COMMAND = CommandDef(
    id="build",
    trigger="/build",
    description="プロジェクトコードベースを構築: 構成、コアモジュール、ストレージ、設定、スクリプト、テスト",
    runbook_purpose="プロジェクトコードベースをゼロから構築します。エージェントはディレクトリ構成を作成し、コアモジュールを実装し、ストレージをセットアップし、設定を記述し、スクリプトを追加し、テストで検証します。",
    worker_specialty="プロジェクトコードベースのゼロからの構築",
    runbook_phases=[
        {"title": "プロジェクト構成", "content": "ディレクトリレイアウトを作成し、パッケージ設定、__init__.pyファイル、仮想環境またはパッケージマネージャーをセットアップ。"},
        {"title": "コアモジュール", "content": "システムの動作を定義する主要モジュールを実装。各モジュールは明確な責任とインターフェースを持つ。"},
        {"title": "ストレージと状態", "content": "データベース、ファイルストレージ、または状態管理をセットアップ。スキーマ、マイグレーション、ヘルパー関数を作成。"},
        {"title": "設定", "content": "環境変数ベースの設定モジュールを作成。閾値、エンドポイント、運用パラメータを定義。"},
        {"title": "統合層", "content": "モジュールを接続。メインエントリポイントとAPIまたはCLIインターフェースを実装。"},
        {"title": "スクリプトとCLI", "content": "適切なフラグとオプション付きの実行スクリプトを構築。一般的な操作用の便利スクリプトを追加。"},
        {"title": "テストと検証", "content": "各モジュールのユニットテストを記述。主要ワークフローの統合テストを追加。すべてのインポートとコマンドが動作することを確認。"},
    ],
)

DEV_ASSIST_BASE_CONFIG = DomainConfig(
    mode="dev-assist",
    workflow_commands=[_BUILD_COMMAND],
    instructions_description="",
)

AGENT_INTEGRATED_BASE_CONFIG = DomainConfig(
    mode="agent-integrated",
    workflow_commands=[
        _BUILD_COMMAND,
        CommandDef(
            id="run",
            trigger="/run",
            description="主要パイプラインまたはワークフローをエンドツーエンドで実行",
            runbook_purpose="プロジェクトの主要ワークフローを最初から最後まで実行します。エージェントは各ステージを実行し、進捗を監視し、エラーを処理し、結果を報告します。",
            worker_specialty="主要プロジェクトワークフローのエンドツーエンド実行",
            runbook_phases=[
                {"title": "事前チェック", "content": "環境、依存関係、設定を確認。ストレージがアクセス可能で、以前の状態が一貫していることを確認。"},
                {"title": "パイプライン実行", "content": "パイプラインの各ステージを順番に実行。進捗とリソース使用量を監視。アイテムごとのエラーをグレースフルに処理。"},
                {"title": "結果の分析", "content": "出力品質を確認し、期待される結果を検証し、異常や失敗にフラグを立てる。"},
                {"title": "報告とクリーンアップ", "content": "結果のサマリーを生成。アーティファクトをアーカイブ。次回実行に向けて状態を更新。"},
            ],
        ),
    ],
    instructions_description="",
)


# ---------------------------------------------------------------------------
# 公開マッピング
# ---------------------------------------------------------------------------

DOMAIN_CONFIGS: Dict[str, DomainConfig] = {
    "ml": ML_CONFIG,
    "web": WEB_CONFIG,
    "devops": DEVOPS_CONFIG,
    "research": RESEARCH_CONFIG,
}
