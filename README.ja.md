# Agentic Engineering Standard (AES)

**エージェント型エンジニアリングプロジェクトの構造化・共有・発見のためのオープンスタンダード。**

AESはエージェントへの指示、スキル、権限、メモリを**ファーストクラスのエンジニアリング成果物**として扱います。`.agent/` ディレクトリに一度定義するだけで、Claude・Cursor・Copilot・Windsurf・Codex・OpenClawに自動コンパイル。ひとつの設定で6つのプラットフォームに対応し、手動での重複作業はゼロです。

**初めての方へ：** [Getting Startedガイド](GETTING-STARTED.md)で、ゼロからの完全なワークフローを確認できます。

## 解決する課題

エージェント型プロジェクトは毎回同じ構造を再発明しています：エージェントへの指示方法、スキルの定義、状態の追跡、権限の設定、コーディング規約の強制、学習内容の保持。各ツールが独自の設定形式を持ち、チームは同じ設定を複数のプラットフォームで複製しています。標準がなく、共有の仕組みがなく、レジストリもありません。

## 解決策

すべてのプロジェクトに `.agent/` ディレクトリを — ツール間で移植可能、チーム間で共有可能、公開レジストリで発見可能：

```
my-project/
  .agent/
    agent.yaml              # マニフェスト — エージェント版の "package.json"
    instructions.md         # マスタープレイブック
    bom.yaml                # Agent Bill of Materials (AI-BOM)
    skills/                 # モジュール式・共有可能なランブック
      ORCHESTRATOR.md
      train.skill.yaml      # 構造化マニフェスト
      train.md              # エージェント用ランブック
    registry/               # 拡張可能なコンポーネント定義
    workflows/              # ステートマシン定義
    commands/               # スラッシュコマンド (/setup, /train, /build, /process)
    permissions.yaml        # エージェントの権限境界
    lifecycle.yaml          # ライフサイクルフック（セッション、ツール、ハートビート）
    memory/                 # エージェントの永続的な学習記録
      decisions/            # 構造化された意思決定記録
    learning/               # 継続学習（インスティンクト、設定）
    rules/                  # コーディングルール・規約
    scripts/                # フック実装スクリプト
    overrides/              # ツール固有の設定 (claude/, cursor/ など)
  .agentignore              # エージェントが触れてはいけないファイル
```

## クイックスタート

```bash
# CLIのインストール
pipx install aes-cli            # 推奨
# cd cli && pip install -e .    # ソースからの場合（venv内で）

# 最新版へのアップデート
pipx upgrade aes-cli            # pipxの場合
# pip install --upgrade aes-cli # pipの場合
# aes sync                      # 更新後に再同期

# 新規AESプロジェクトの作成
aes init

# .agent/ ディレクトリの検証
aes validate

# ツール固有の設定を生成（ツール選択プロンプト付き）
aes sync

# 前回のsync以降の変更を確認
aes status

# レジストリの検索
aes search "deploy"
aes search --type template

# レジストリからスキルをインストール
aes install aes-hub/deploy@^1.0.0

# 共有テンプレートからプロジェクトを初期化
aes init --from aes-hub/ml-pipeline@^2.0

# スキルの公開
aes publish ./my-skill -o dist/

# .agent/ 設定全体をテンプレートとして公開
aes publish --template --registry -o dist/              # デフォルトは公開
aes publish --skill train --registry --visibility private  # 非公開パッケージ
```

## 仕様

完全な仕様は [`spec/`](spec/) にあります：

| # | ドキュメント | 定義内容 |
|---|------------|---------|
| 01 | [マニフェスト](spec/01-manifest.md) | `agent.yaml` — アイデンティティ、スキル、依存関係、環境 |
| 02 | [インストラクション](spec/02-instructions.md) | `instructions.md` — マスタープレイブック |
| 03 | [スキル](spec/03-skills.md) | ポータブルなスキル定義（マニフェスト＋ランブック） |
| 04 | [レジストリ](spec/04-registries.md) | 拡張可能なコンポーネントカタログ |
| 05 | [ワークフロー](spec/05-workflows.md) | ステートマシン定義 |
| 06 | [パーミッション](spec/06-permissions.md) | エージェントの権限境界 |
| 07 | [メモリ](spec/07-memory.md) | エージェントの永続的な学習 |
| 08 | [コマンド](spec/08-commands.md) | マルチフェーズのワークフロー自動化 |
| 09 | [シェアリング](spec/09-sharing.md) | 公開、バージョニング、依存関係 |
| 10 | [Agentignore](spec/10-agentignore.md) | `.agentignore` フォーマット |
| 11 | [BOM](spec/11-bom.md) | Agent Bill of Materials (AI-BOM) |
| 12 | [意思決定記録](spec/12-decision-records.md) | 構造化されたエージェント意思決定の監査証跡 |
| 13 | [ライフサイクル](spec/13-lifecycle.md) | プラットフォーム非依存のライフサイクルフック |
| 14 | [ラーニング](spec/14-learning.md) | インスティンクトによる継続学習 |
| 15 | [ルール](spec/15-rules.md) | コーディングルールと規約 |

## CLIツール

`aes` CLI (`cli/`) が提供するコマンド：

| コマンド | 説明 |
|---------|------|
| `aes init` | `.agent/` ディレクトリの作成（モード＋タイプの2段階選択、または自動検出） |
| `aes validate [path]` | JSONスキーマ＋依存関係グラフによるバリデーション |
| `aes inspect [path\|name]` | プロジェクト構造（ローカル）またはレジストリパッケージ詳細（リモート）の表示 |
| `aes sync [path]` | ツール固有の設定を生成（ターゲット選択プロンプト付き） |
| `aes status [path]` | 前回のsync以降の `.agent/` の変更を表示 |
| `aes publish [skill]` | スキルをtarballにパッケージ化、オプションでレジストリにアップロード（`--registry`） |
| `aes publish --template` | `.agent/` ディレクトリ全体を共有可能なテンプレートにパッケージ化 |
| `aes install [source]` | tarball、ローカルディレクトリ、またはAESレジストリからスキルをインストール |
| `aes search [query]` | AESパッケージレジストリを検索（`--sort-by`、`--limit`、`-v` 対応） |
| `aes bom [path]` | Agent Bill of Materials（モデル、フレームワーク、ツール、データソース）を表示 |
| `aes upgrade [path]` | `.agent/` を現在のスペックバージョンにアップグレード（デフォルトはdry-run、`--apply` で実行） |

## MCPサーバー

`aes-mcp` コマンドはAESレジストリを [Model Context Protocol](https://modelcontextprotocol.io/) ツールサーバーとして公開し、MCP対応エージェントがパッケージを直接検索・インストール・公開できるようにします。

```bash
# MCP拡張機能付きでインストール
pipx install "aes-cli[mcp]"

# ソースから（venv内で）
# cd cli && pip install -e ".[mcp]"

# MCPサーバーの起動
aes-mcp
```

`aes init` は `.mcp.json` 設定ファイルを自動生成し、MCP対応ツールがサーバーを自動検出できるようにします。

## Webダッシュボード

GitHub OAuthによるレジストリAPIトークン管理ダッシュボードが `web/` にあります。`aes-official.com` でGitHub認証を行い、`aes publish` 用のトークンを作成・失効できるセルフサービスUIを提供しています。

## サンプル & テンプレート

[`examples/`](examples/) に4つのリファレンス実装、[`templates/`](templates/) にインストール可能なドメインテンプレートがあります：

| サンプル | ドメイン | モード | スキル | ワークフローコマンド |
|---------|---------|--------|--------|-------------------|
| [ml-pipeline](examples/ml-pipeline/) | 機械学習 | Agent-Integrated | discover, examine, train, ... | `/train` |
| [web-app](examples/web-app/) | Web開発 | Dev-Assist | scaffold, test, deploy, ... | `/build` |
| [devops](examples/devops/) | インフラ | Dev-Assist | provision, deploy, rollback, ... | `/provision` |
| [personal-assistant](examples/personal-assistant/) | アシスタント | Agent-Integrated | greeting, web-search | `/converse` |

`templates/` ディレクトリには、新規プロジェクトの出発点として使える検証済みAESスキルパッケージが含まれています。MLは完全な7段階パイプライン、webは5スキル、devopsは5スキル、**research** はコンテンツ処理パイプライン用の5スキル、**assistant** は24/7エージェント向けにidentity/model/channelsをスキャフォールドします。

### モード

AESはエージェント型プロジェクトを2種類に区別します：

- **Dev-Assist** — エージェントがプロジェクトを構築します（スキャフォールド、実装、テスト、デプロイ）。リリース後は主な役割を終えますが、メンテナンスやバグ修正には引き続き対応できます。（Web、API、CLI、ライブラリ、DevOps）
- **Agent-Integrated** — エージェントが稼働中のプロダクトに組み込まれています。モデルのトレーニング、コンテンツの処理、データの取り込みなど、システムの一部として継続的に動作します。エージェントなしではプロダクトが機能しません。（MLパイプライン、リサーチパイプライン、パーソナルアシスタント）

`aes init` は2段階の選択式ピッカーを表示：モードを選択後、プロジェクトタイプを選択。各ドメインはワークフローコマンド（例：`/train`、`/build`、`/process`）とパイプライン追跡用のオペレーションメモリファイルを自動生成します。

## レジストリ

AESにはスキルとテンプレートを共有するためのパッケージレジストリが `registry.aes-official.com` にあります：

```bash
# スキルとテンプレートの検索
aes search "deploy"
aes search --tag ml
aes search --domain devops
aes search --type template          # テンプレートのみ
aes search --type skill             # スキルのみ
aes search --sort-by version        # semverでソート（最新が先頭）
aes search --limit 5 -v             # 上位5件、詳細表示

# リモートパッケージの詳細表示
aes inspect deploy                  # レジストリの最新バージョン
aes inspect deploy@1.0.0            # 特定のバージョン

# レジストリからスキルをインストール
aes install aes-hub/deploy@^1.0.0

# 共有テンプレートからプロジェクトを初期化
aes init --from aes-hub/ml-pipeline@^2.0

# スキルをレジストリに公開（AES_REGISTRY_KEY が必要）
aes publish --skill train --registry -o dist/

# .agent/ 設定全体をテンプレートとして公開
aes publish --template --registry -o dist/
```

バージョン解決は次の形式に対応：完全一致（`1.2.3`）、キャレット（`^1.2.0`）、チルダ（`~1.2.0`）、最小（`>=1.0.0`）、ワイルドカード（`*`）。

### テンプレート vs スキル

| | スキル | テンプレート |
|---|--------|------------|
| **内容** | 単一の機能（マニフェスト＋ランブック） | 完全な `.agent/` 設定 |
| **インストール** | `aes install aes-hub/name@^1.0` | `aes init --from aes-hub/name@^1.0` |
| **公開** | `aes publish --skill X --registry` | `aes publish --template --registry` |
| **配置先** | `.agent/skills/vendor/` | `.agent/`（ディレクトリ全体） |

テンプレートはデフォルトで `memory/`、`local.yaml`、`overrides/` を除外し、機密データを保護します。`--include-memory` または `--include-all` でオーバーライドできます。

## 設計原則

1. **一度定義し、どこでもコンパイル** — `.agent/` が唯一の情報源、`aes sync` が6プラットフォームにコンパイル
2. **ツール非依存** — Claude、Cursor、Copilot、Windsurf、Codex、OpenClaw、または将来のエージェントツールに対応
3. **ドメイン非依存** — ML、Web、DevOps、リサーチ、アシスタント、データパイプライン、何でも対応
4. **組み合わせ可能** — スキル、テンプレート、インスティンクト、ルールパックはレジストリ経由で個別に共有可能
5. **学習するエージェント** — ライフサイクルフックがセッションからパターンを抽出し、信頼度スコア付きインスティンクトとして進化
6. **コードよりコンフィグ** — エージェントが変更するのは設定であり、オーケストレーションロジックではない
7. **暗黙より明示** — ステートマシン、権限、規約、意思決定は宣言され、隠蔽されない

## JSONスキーマ

[`schemas/`](schemas/) のバリデーションスキーマにより、IDEの自動補完やCIバリデーションが可能です：

- `agent.schema.json` — `agent.yaml` のバリデーション
- `skill.schema.json` — `*.skill.yaml` のバリデーション
- `workflow.schema.json` — ワークフロー定義のバリデーション
- `registry.schema.json` — コンポーネントレジストリのバリデーション
- `permissions.schema.json` — `permissions.yaml` のバリデーション
- `bom.schema.json` — `bom.yaml` (AI-BOM) のバリデーション
- `decision-record.schema.json` — 意思決定記録のバリデーション
- `lifecycle.schema.json` — `lifecycle.yaml` のバリデーション
- `instinct.schema.json` — `.instinct.yaml` ファイルのバリデーション
- `learning-config.schema.json` — 学習設定 `config.yaml` のバリデーション
- `rules-config.schema.json` — ルール設定 `rules.yaml` のバリデーション

## Syncターゲット

`aes sync` は `.agent/` をツール固有の設定にコンパイルします（6プラットフォーム対応）：

| ターゲット | コマンド | 出力 |
|-----------|---------|------|
| Claude Code | `aes sync -t claude` | `CLAUDE.md` + `.claude/settings.local.json` + hooks.json + rules/ |
| Cursor | `aes sync -t cursor` | `.cursorrules` |
| Copilot | `aes sync -t copilot` | `.github/copilot-instructions.md` |
| Windsurf | `aes sync -t windsurf` | `.windsurfrules` |
| Codex | `aes sync -t codex` | `AGENTS.md` + `.agents/skills/` |
| OpenClaw | `aes sync -t openclaw` | `.openclaw/` (openclaw.json, workspace/, policy.yaml) |

## ライセンス

Apache 2.0 — [LICENSE](LICENSE) を参照
