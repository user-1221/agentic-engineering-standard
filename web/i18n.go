package main

import (
	"html/template"
	"net/http"
	"strings"
)

// Translations holds all translated strings for a language.
// Values are template.HTML so strings containing HTML tags are not escaped.
type Translations map[string]template.HTML

// detectLang returns "ja" if the client's most preferred language is Japanese,
// otherwise returns "en".
func detectLang(r *http.Request) string {
	accept := r.Header.Get("Accept-Language")
	if accept == "" {
		return "en"
	}
	parts := strings.Split(accept, ",")
	if len(parts) > 0 {
		tag := strings.TrimSpace(strings.SplitN(parts[0], ";", 2)[0])
		if strings.HasPrefix(strings.ToLower(tag), "ja") {
			return "ja"
		}
	}
	return "en"
}

// getTranslations returns the translation map for the given language code.
func getTranslations(lang string) Translations {
	if lang == "ja" {
		return translationsJA
	}
	return translationsEN
}

// ---------------------------------------------------------------------------
// English translations
// ---------------------------------------------------------------------------

var translationsEN = Translations{
	// -- Meta / Title --
	"site_title":   "AES &mdash; Agentic Engineering Standard",
	"meta_desc":    "AES is the open standard for giving AI agents persistent memory, skills, and project context. Structured once, useful forever — across every AI tool.",
	"og_title":     "AES &mdash; The Open Standard for Agent Engineering",
	"og_desc":      "Give AI agents persistent memory, skills, and deep project context. Works across Claude, Cursor, Copilot, Windsurf, Codex, and OpenClaw.",
	"twitter_desc": "Give AI agents persistent memory, skills, and deep project context.",

	// -- Nav --
	"skip_content":  "Skip to content",
	"nav_docs":      "Docs",
	"nav_dashboard": "Dashboard",
	"nav_signin":    "Sign in with GitHub",
	"nav_home":      "Home",
	"nav_logout":    "Logout",
	"nav_how":       "How It Works",
	"nav_examples":  "Examples",
	"nav_registry":  "Registry",

	// -- Hero --
	"hero_badge":   "Open Standard &middot; v1.4",
	"hero_title":   `The open standard for<br><span class="hero-gradient">agent engineering</span>.`,
	"hero_tagline": "Give your AI agents persistent memory, deep project knowledge, and real skills &mdash; structured once, useful forever, portable across every tool.",

	// -- CTA --
	"cta_get_started": "Get Started",
	"cta_github":      "View on GitHub",
	"cta_try":         "Try in 60s",

	// -- Hero tree labels --
	"tree_identity":     "Identity",
	"tree_capabilities": "Capabilities",
	"tree_persistence":  "Persistence",

	// -- Why section --
	"why_problem_label": "The problem",
	"why_problem_title": "Every session starts from zero",
	"why_problem_desc":  "Your agent doesn&rsquo;t know your architecture, conventions, or deployment. You re-explain every session.",
	"why_solution_label": "The standard",
	"why_solution_title": "Every session builds on the last",
	"why_solution_desc":  "AES gives your agent structured memory, real skills, and deep project context. Checked into git, portable across tools.",

	// -- Anatomy section --
	"anatomy_label": "What you&rsquo;re building",
	"anatomy_title": `Your project&rsquo;s <code>.agent/</code> brain`,
	"anatomy_desc":  "Identity, skills, memory, and permissions &mdash; one directory, checked into git.",

	// -- Tree annotations --
	"ann_agent":        "# Who the agent is",
	"ann_instructions": "# How it thinks about your project",
	"ann_permissions":  "# What it&rsquo;s allowed to do",
	"ann_skills":       "# What it knows how to do",
	"ann_workflows":    "# How work flows through stages",
	"ann_memory":       "# What it&rsquo;s learned over time",
	"ann_commands":     "# Complex tasks it can run",
	"ann_registry":     "# Installed community skills",

	// -- Terminal --
	"term_1": "# Install in seconds",
	"term_2": "# Give your project structured agent context",
	"term_3": "# Make sure your agent setup is complete",
	"term_4": "# Find proven skills others have built",
	"term_5": "# Add deployment expertise to your agent",

	// -- How it works --
	"how_label":      "How it works",
	"how_title":      "Three steps to a smarter agent",
	"how_step1_title": "Initialize",
	"how_step1_desc":  "<code>aes init</code> scaffolds a <code>.agent/</code> directory tailored to your project",
	"how_step2_title": "Develop",
	"how_step2_desc":  "Your agent learns your codebase. Memory builds. Skills get refined every session",
	"how_step3_title": "Share",
	"how_step3_desc":  "Publish skills to the registry. Install templates. Reuse across every project",

	// -- Features --
	"feat_label":       "Why it matters",
	"feat_title":       "Built for how you actually work",
	"feat_dev_title":   "For individual developers",
	"feat_dev_benefit": "Your agent becomes a specialist",
	"feat_dev_1":       "Templates give your agent domain expertise out of the box &mdash; ML, web, DevOps, research",
	"feat_dev_2":       "Install proven skills from the registry. One command, zero learning curve",
	"feat_dev_3":       "Memory persists across sessions. Every conversation makes your agent smarter",
	"feat_dev_4":       "Works across Claude, Cursor, Copilot, Windsurf, Codex, OpenClaw &mdash; switch without starting over",
	"feat_team_title":   "For teams",
	"feat_team_benefit": "Every AI works from the same architecture",
	"feat_team_1":       "Every agent works from the same architecture, conventions, and design principles",
	"feat_team_2":       `New teammate? <code>aes init --from your-team/template</code> &mdash; instant project context`,
	"feat_team_3":       `Instructions, permissions, and skills live in <code>.agent/</code>, always in sync via git`,
	"feat_team_4":       "Ship independently. Everything fits because agents share the same foundation",

	// -- Stats --
	"stat_templates": "Domain templates",
	"stat_skills":    "Community skills",
	"stat_tools":     "AI tools supported",
	"stat_standard":  "Standard to learn",
	"stat_agents":    "24/7 agents",

	// -- Ecosystem --
	"eco_label":    "The ecosystem",
	"eco_title":    "A growing library of agent skills",
	"eco_desc":     "Install proven skills built by experienced engineers. One command, zero learning curve.",
	"eco_deploy":   "CI/CD &amp; infrastructure",
	"eco_review":   "Quality &amp; best practices",
	"eco_security": "Vulnerability scanning",
	"eco_db":       "Schema migrations",
	"eco_ml":       "Training &amp; evaluation",
	"eco_docs":     "API documentation",
	"eco_cta":      "Browse the registry &rarr;",

	// -- Compare --
	"cmp_label":   "See the difference",
	"cmp_without": "Without AES",
	"cmp_with":    "With AES",
	"cmp_you":     "You",
	"cmp_agent":   "Agent",
	// Without AES dialogue
	"cmp_w1":   "Deploy the app to staging",
	"cmp_a1":   "What&rsquo;s your deployment process?",
	"cmp_w2":   "Docker + GitHub Actions, like I said last time...",
	"cmp_a2":   "What registry do you push to?",
	"cmp_w3":   "ECR. I already told you this yesterday",
	"cmp_a3":   "What are the environment variables?",
	"cmp_fade": "...20 messages later, still configuring",
	// With AES dialogue
	"cmp_with_w1":   "Deploy the app to staging",
	"cmp_with_a1":   "Running deploy skill...",
	"cmp_with_s1":   "Built Docker image <code>app:v2.4.1</code>",
	"cmp_with_s2":   "Pushed to ECR staging registry",
	"cmp_with_s3":   "Deployed via GitHub Actions",
	"cmp_with_done": "Staging is live at staging.app.com",

	// -- Sync Everywhere (home) --
	"sync_label": "Sync everywhere",
	"sync_title": "One standard. Six tools.",
	"sync_desc":  "Write once in <code>.agent/</code> &mdash; sync to any tool with a single command.",

	// -- How It Works page --
	"hiw_title":           "How It Works &mdash; AES",
	"hiw_hero_label":      "The workflow",
	"hiw_hero_title":      "From zero to production-ready agent",
	"hiw_hero_desc":       "Four steps to give your AI agent persistent memory, real skills, and deep project context.",
	"hiw_step1_label":     "Step 1",
	"hiw_step1_title":     "Initialize",
	"hiw_step1_desc":      "<code>aes init</code> scaffolds a <code>.agent/</code> directory tailored to your project type &mdash; ML, Web, DevOps, Research, or Assistant.",
	"hiw_step2_label":     "Step 2",
	"hiw_step2_title":     "Define",
	"hiw_step2_desc":      "Configure your agent&rsquo;s identity in <code>agent.yaml</code>, define skills with runbooks, and set fine-grained permissions.",
	"hiw_step3_label":     "Step 3",
	"hiw_step3_title":     "Sync",
	"hiw_step3_desc":      "<code>aes sync</code> translates your <code>.agent/</code> directory into the native format of each AI tool. One source, six outputs.",
	"hiw_step4_label":     "Step 4",
	"hiw_step4_title":     "Share",
	"hiw_step4_desc":      "Publish skills and templates to the registry. Install proven patterns from the community. Reuse across every project.",
	"hiw_targets_title":   "What each tool gets",
	"hiw_target_claude":   "<code>CLAUDE.md</code> + <code>.claude/settings.local.json</code> + <code>.claude/commands/skills/*.md</code>",
	"hiw_target_cursor":   "<code>.cursorrules</code>",
	"hiw_target_copilot":  "<code>.github/copilot-instructions.md</code>",
	"hiw_target_windsurf": "<code>.windsurfrules</code>",
	"hiw_target_openclaw": "<code>.openclaw/openclaw.json</code> + workspace Markdown + <code>SKILL.md</code> files",
	"hiw_target_codex":    "<code>AGENTS.md</code> + <code>.agents/skills/&lt;id&gt;/SKILL.md</code>",
	"hiw_cta":             "Ready to start?",

	// -- Examples page --
	"ex_title":            "Examples &mdash; AES",
	"ex_hero_label":       "Examples",
	"ex_hero_title":       "See AES in action",
	"ex_hero_desc":        "Five project types, five domains. Each example is a validated AES project you can explore or use as a starting point.",
	"ex_assistant_name":   "Personal Assistant",
	"ex_assistant_desc":   "A 24/7 AI assistant with identity, heartbeat, and channel integration. Built for the OpenClaw runtime.",
	"ex_assistant_skills": "greeting, web-search",
	"ex_ml_name":          "ML Model Factory",
	"ex_ml_desc":          "End-to-end ML pipeline: data discovery, model training, and evaluation with experiment tracking.",
	"ex_ml_skills":        "discover, train, evaluate",
	"ex_web_name":         "SaaS Dashboard",
	"ex_web_desc":         "Full-stack web application with component scaffolding, testing, and deployment automation.",
	"ex_web_skills":       "scaffold, test, deploy",
	"ex_devops_name":      "Infra Autopilot",
	"ex_devops_desc":      "Infrastructure automation with provisioning, deployment, and rollback capabilities.",
	"ex_devops_skills":    "provision, deploy, rollback",
	"ex_research_name":    "Research Pipeline",
	"ex_research_desc":    "Automated research workflow: ingest papers, analyze findings, and generate structured reports.",
	"ex_research_skills":  "ingest, analyze, report",
	"ex_mode_title":       "Two modes of operation",
	"ex_mode_dev_title":   "Dev-Assist",
	"ex_mode_dev_desc":    "The agent builds the project, then steps back. You drive, the agent assists. Best for Web and DevOps projects.",
	"ex_mode_agent_title": "Agent-Integrated",
	"ex_mode_agent_desc":  "The agent is embedded in the running product. It operates autonomously with identity and memory. Best for ML, Research, and Assistant projects.",
	"ex_new_badge":        "NEW",
	"ex_cta":              "Start your own project",
	"ex_mode_dev_label":   "dev-assist",
	"ex_mode_agent_label": "agent-integrated",

	// -- Bottom CTA --
	"bottom_cta": "Stop re-explaining your codebase to AI",
	"copy":       "Copy",
	"copied":     "Copied!",

	// -- Footer --
	"footer_open_source":   "Open Source",
	"footer_apache":        "Apache 2.0",
	"footer_tool_agnostic": "Tool Agnostic",
	"footer_tagline":       "Your agents should know your project as well as your senior engineers do.",

	// -- Registry page --
	"reg_title":           "Registry &mdash; AES",
	"reg_label":           "Registry",
	"reg_h1":              "Skills &amp; Templates",
	"reg_desc":            "Discover proven skills and templates built by the community. Install with a single command.",
	"reg_empty":           "No packages published yet. Be the first to publish!",
	"reg_more_count_pre":  "There are ",
	"reg_more_count_post": " packages in total. Sign in to see all of them.",
	"reg_see_more":        "Sign in with GitHub to see more",
	"reg_cli_title":       "Use the CLI",
	"reg_cli_search":      "# Search for skills",
	"reg_cli_install":     "# Install a skill",

	// -- Dashboard --
	"dash_title":          "Dashboard &mdash; AES",
	"dash_h1":             "Registry Tokens",
	"dash_subtitle":       "Tokens let you publish skills and templates to the AES registry.",
	"dash_th_name":        "Name",
	"dash_th_created":     "Created",
	"dash_revoke":         "Revoke",
	"dash_revoke_prefix":  "Revoke token ",
	"dash_revoke_suffix":  "?",
	"dash_empty":          "No tokens yet. Create one below.",
	"dash_create_title":   "Create New Token",
	"dash_token_label":    "Token name",
	"dash_token_hint":     "Letters, numbers, hyphens, and underscores. Prefixed with your GitHub username.",
	"dash_create_btn":     "Create Token",
	"dash_max_pre":        "You&rsquo;ve reached the maximum of ",
	"dash_max_post":       " tokens. Revoke one to create a new one.",
	"dash_usage_title":    "Usage",
	"dash_usage_set_tok":  "# Set your token",
	"dash_usage_set_url":  "# Set the registry URL",
	"dash_usage_pub_skill": "# Publish a skill",
	"dash_usage_pub_tmpl": "# Publish a template",

	// -- Error page --
	"err_title":   "Error &mdash; AES",
	"err_heading": "Something went wrong",
	"err_go_home": "Go Home",

	// -- Token created page --
	"tc_title":   "Token Created &mdash; AES",
	"tc_loading": "Activating token",
	"tc_heading": "Token Created",
	"tc_warning": "Copy this token now. It will not be shown again.",
	"tc_copy":    "Copy",
	"tc_setup":   "Set up your environment",
	"tc_back":    "Back to Dashboard",
}

// ---------------------------------------------------------------------------
// Japanese translations
// ---------------------------------------------------------------------------

var translationsJA = Translations{
	// -- Meta / Title --
	"site_title":   "AES &mdash; エージェンティック・エンジニアリング・スタンダード",
	"meta_desc":    "AESは、AIエージェントに永続的なメモリ、スキル、プロジェクトコンテキストを与えるオープンスタンダードです。一度構造化すれば、あらゆるAIツールでずっと活用できます。",
	"og_title":     "AES &mdash; エージェントエンジニアリングのオープンスタンダード",
	"og_desc":      "AIエージェントに永続的なメモリ、スキル、深いプロジェクトコンテキストを。Claude、Cursor、Copilot、Windsurf、Codex、OpenClawに対応。",
	"twitter_desc": "AIエージェントに永続的なメモリ、スキル、深いプロジェクトコンテキストを。",

	// -- Nav --
	"skip_content":  "コンテンツにスキップ",
	"nav_docs":      "ドキュメント",
	"nav_dashboard": "ダッシュボード",
	"nav_signin":    "GitHubでサインイン",
	"nav_home":      "ホーム",
	"nav_logout":    "ログアウト",
	"nav_how":       "使い方",
	"nav_examples":  "事例",
	"nav_registry":  "レジストリ",

	// -- Hero --
	"hero_badge":   "オープンスタンダード &middot; v1.4",
	"hero_title":   `<span class="hero-gradient">エージェントエンジニアリング</span>の<br>オープンスタンダード。`,
	"hero_tagline": "AIエージェントに永続メモリ、深いプロジェクト知識、実用的なスキルを &mdash; 一度構造化すれば、すべてのツールで永続的に活用。",

	// -- CTA --
	"cta_get_started": "はじめる",
	"cta_github":      "GitHubで見る",
	"cta_try":         "60秒で試す",

	// -- Hero tree labels --
	"tree_identity":     "定義",
	"tree_capabilities": "機能",
	"tree_persistence":  "永続化",

	// -- Why section --
	"why_problem_label": "課題",
	"why_problem_title": "毎回ゼロからのスタート",
	"why_problem_desc":  "エージェントはアーキテクチャも規約もデプロイ方法も知りません。毎回説明し直す必要があります。",
	"why_solution_label": "標準規格",
	"why_solution_title": "毎回のセッションが前回の続きから",
	"why_solution_desc":  "AESはエージェントに構造化されたメモリ、実用的なスキル、深いプロジェクトコンテキストを与えます。gitで管理、あらゆるツールで利用可能。",

	// -- Anatomy section --
	"anatomy_label": "全体構造",
	"anatomy_title": `プロジェクトの<code>.agent/</code>ブレイン`,
	"anatomy_desc":  "アイデンティティ、スキル、メモリ、権限 &mdash; 1つのディレクトリで、gitに保存。",

	// -- Tree annotations --
	"ann_agent":        "# エージェントの定義",
	"ann_instructions": "# プロジェクトの理解方法",
	"ann_permissions":  "# 許可される操作",
	"ann_skills":       "# 実行可能なスキル",
	"ann_workflows":    "# 作業フローの定義",
	"ann_memory":       "# 蓄積された知識",
	"ann_commands":     "# 実行可能なコマンド",
	"ann_registry":     "# インストール済みスキル",

	// -- Terminal --
	"term_1": "# 数秒でインストール",
	"term_2": "# プロジェクトに構造化されたエージェントコンテキストを",
	"term_3": "# エージェント設定の検証",
	"term_4": "# 他の開発者が作った実証済みスキルを検索",
	"term_5": "# デプロイのスキルをエージェントに追加",

	// -- How it works --
	"how_label":       "使い方",
	"how_title":       "3ステップでスマートなエージェントへ",
	"how_step1_title": "初期化",
	"how_step1_desc":  "<code>aes init</code>でプロジェクトに合わせた<code>.agent/</code>ディレクトリを生成",
	"how_step2_title": "開発",
	"how_step2_desc":  "エージェントがコードベースを学習。メモリが蓄積。スキルがセッションごとに洗練",
	"how_step3_title": "共有",
	"how_step3_desc":  "スキルをレジストリに公開。テンプレートをインストール。すべてのプロジェクトで再利用",

	// -- Features --
	"feat_label":       "なぜ重要か",
	"feat_title":       "実際の開発ワークフローに最適化",
	"feat_dev_title":   "個人開発者向け",
	"feat_dev_benefit": "エージェントがスペシャリストに",
	"feat_dev_1":       "テンプレートでML、Web、DevOps、リサーチなどの専門知識を即座に付与",
	"feat_dev_2":       "レジストリから実証済みスキルをインストール。コマンド1つ、学習コストゼロ",
	"feat_dev_3":       "メモリがセッション間で永続化。会話を重ねるほどエージェントが賢く",
	"feat_dev_4":       "Claude、Cursor、Copilot、Windsurf、Codex、OpenClawに対応 &mdash; ツールを変えてもやり直し不要",
	"feat_team_title":   "チーム向け",
	"feat_team_benefit": "すべてのAIが同じアーキテクチャで動作",
	"feat_team_1":       "すべてのエージェントが同じアーキテクチャ、規約、設計原則で動作",
	"feat_team_2":       `新メンバー？ <code>aes init --from your-team/template</code> &mdash; 即座にプロジェクトコンテキストを共有`,
	"feat_team_3":       `指示、権限、スキルは<code>.agent/</code>に集約、gitで常に同期`,
	"feat_team_4":       "独立して出荷可能。エージェントが同じ基盤を共有しているから、すべてが統合される",

	// -- Stats --
	"stat_templates": "ドメインテンプレート",
	"stat_skills":    "コミュニティスキル",
	"stat_tools":     "対応AIツール",
	"stat_standard":  "学ぶべきスタンダード",
	"stat_agents":    "24/7エージェント",

	// -- Ecosystem --
	"eco_label":    "エコシステム",
	"eco_title":    "成長し続けるエージェントスキルライブラリ",
	"eco_desc":     "経験豊富なエンジニアが作った実証済みスキルをインストール。コマンド1つ、学習コストゼロ。",
	"eco_deploy":   "CI/CD &amp; インフラ",
	"eco_review":   "品質 &amp; ベストプラクティス",
	"eco_security": "脆弱性スキャン",
	"eco_db":       "スキーママイグレーション",
	"eco_ml":       "学習 &amp; 評価",
	"eco_docs":     "APIドキュメント",
	"eco_cta":      "レジストリを見る &rarr;",

	// -- Compare --
	"cmp_label":   "違いを見る",
	"cmp_without": "AESなし",
	"cmp_with":    "AESあり",
	"cmp_you":     "あなた",
	"cmp_agent":   "エージェント",
	// Without AES dialogue
	"cmp_w1":   "アプリをステージングにデプロイして",
	"cmp_a1":   "デプロイプロセスを教えてください。",
	"cmp_w2":   "Docker + GitHub Actions、前にも言ったけど...",
	"cmp_a2":   "どのレジストリにプッシュしますか？",
	"cmp_w3":   "ECR。昨日も言ったのに",
	"cmp_a3":   "環境変数は何ですか？",
	"cmp_fade": "...20メッセージ後、まだ設定中",
	// With AES dialogue
	"cmp_with_w1":   "アプリをステージングにデプロイして",
	"cmp_with_a1":   "デプロイスキルを実行中...",
	"cmp_with_s1":   "Dockerイメージ <code>app:v2.4.1</code> をビルド",
	"cmp_with_s2":   "ECRステージングレジストリにプッシュ",
	"cmp_with_s3":   "GitHub Actions経由でデプロイ",
	"cmp_with_done": "ステージング環境が staging.app.com で稼働中",

	// -- Sync Everywhere (home) --
	"sync_label": "どこでも同期",
	"sync_title": "1つの標準。6つのツール。",
	"sync_desc":  "<code>.agent/</code>で一度書けば &mdash; コマンド1つであらゆるツールに同期。",

	// -- How It Works page --
	"hiw_title":           "使い方 &mdash; AES",
	"hiw_hero_label":      "ワークフロー",
	"hiw_hero_title":      "ゼロから本番対応エージェントへ",
	"hiw_hero_desc":       "4つのステップでAIエージェントに永続メモリ、実用的なスキル、深いプロジェクトコンテキストを。",
	"hiw_step1_label":     "ステップ1",
	"hiw_step1_title":     "初期化",
	"hiw_step1_desc":      "<code>aes init</code>でプロジェクトタイプに合わせた<code>.agent/</code>ディレクトリを生成 &mdash; ML、Web、DevOps、Research、Assistantに対応。",
	"hiw_step2_label":     "ステップ2",
	"hiw_step2_title":     "定義",
	"hiw_step2_desc":      "<code>agent.yaml</code>でエージェントのアイデンティティを設定、ランブック付きスキルを定義、きめ細かい権限を設定。",
	"hiw_step3_label":     "ステップ3",
	"hiw_step3_title":     "同期",
	"hiw_step3_desc":      "<code>aes sync</code>で<code>.agent/</code>ディレクトリを各AIツールのネイティブ形式に変換。1つのソース、6つの出力。",
	"hiw_step4_label":     "ステップ4",
	"hiw_step4_title":     "共有",
	"hiw_step4_desc":      "スキルとテンプレートをレジストリに公開。コミュニティの実証済みパターンをインストール。すべてのプロジェクトで再利用。",
	"hiw_targets_title":   "各ツールが受け取るもの",
	"hiw_target_claude":   "<code>CLAUDE.md</code> + <code>.claude/settings.local.json</code> + <code>.claude/commands/skills/*.md</code>",
	"hiw_target_cursor":   "<code>.cursorrules</code>",
	"hiw_target_copilot":  "<code>.github/copilot-instructions.md</code>",
	"hiw_target_windsurf": "<code>.windsurfrules</code>",
	"hiw_target_openclaw": "<code>.openclaw/openclaw.json</code> + ワークスペースMarkdown + <code>SKILL.md</code>ファイル",
	"hiw_target_codex":    "<code>AGENTS.md</code> + <code>.agents/skills/&lt;id&gt;/SKILL.md</code>",
	"hiw_cta":             "始める準備はできましたか？",

	// -- Examples page --
	"ex_title":            "事例 &mdash; AES",
	"ex_hero_label":       "事例",
	"ex_hero_title":       "AESの実例を見る",
	"ex_hero_desc":        "5つのプロジェクトタイプ、5つのドメイン。各事例は検証済みのAESプロジェクトで、探索やスタートポイントとして利用可能。",
	"ex_assistant_name":   "パーソナルアシスタント",
	"ex_assistant_desc":   "アイデンティティ、ハートビート、チャネル統合を備えた24/7 AIアシスタント。OpenClawランタイム向け。",
	"ex_assistant_skills": "greeting, web-search",
	"ex_ml_name":          "MLモデルファクトリー",
	"ex_ml_desc":          "エンドツーエンドMLパイプライン：データ探索、モデル学習、実験追跡による評価。",
	"ex_ml_skills":        "discover, train, evaluate",
	"ex_web_name":         "SaaSダッシュボード",
	"ex_web_desc":         "フルスタックWebアプリ：コンポーネントスキャフォールド、テスト、デプロイ自動化。",
	"ex_web_skills":       "scaffold, test, deploy",
	"ex_devops_name":      "インフラオートパイロット",
	"ex_devops_desc":      "プロビジョニング、デプロイ、ロールバック機能を備えたインフラ自動化。",
	"ex_devops_skills":    "provision, deploy, rollback",
	"ex_research_name":    "リサーチパイプライン",
	"ex_research_desc":    "自動リサーチワークフロー：論文取得、分析、構造化レポート生成。",
	"ex_research_skills":  "ingest, analyze, report",
	"ex_mode_title":       "2つの動作モード",
	"ex_mode_dev_title":   "Dev-Assist",
	"ex_mode_dev_desc":    "エージェントがプロジェクトを構築し、完了後は後退。あなたが主導し、エージェントがアシスト。WebとDevOpsプロジェクトに最適。",
	"ex_mode_agent_title": "Agent-Integrated",
	"ex_mode_agent_desc":  "エージェントが稼働中のプロダクトに組み込まれる。アイデンティティとメモリで自律的に動作。ML、Research、Assistantプロジェクトに最適。",
	"ex_new_badge":        "NEW",
	"ex_cta":              "自分のプロジェクトを始める",
	"ex_mode_dev_label":   "dev-assist",
	"ex_mode_agent_label": "agent-integrated",

	// -- Bottom CTA --
	"bottom_cta": "AIにコードベースを何度も説明するのはもうやめよう",
	"copy":       "コピー",
	"copied":     "コピー完了！",

	// -- Footer --
	"footer_open_source":   "オープンソース",
	"footer_apache":        "Apache 2.0",
	"footer_tool_agnostic": "ツール非依存",
	"footer_tagline":       "エージェントは、シニアエンジニアと同じくらいプロジェクトを理解すべきです。",

	// -- Registry page --
	"reg_title":           "レジストリ &mdash; AES",
	"reg_label":           "レジストリ",
	"reg_h1":              "スキル &amp; テンプレート",
	"reg_desc":            "コミュニティが作った実証済みのスキルとテンプレートを発見。コマンド1つでインストール。",
	"reg_empty":           "まだパッケージが公開されていません。最初の公開者になりましょう！",
	"reg_more_count_pre":  "全",
	"reg_more_count_post": "パッケージ。すべてを見るにはサインインしてください。",
	"reg_see_more":        "GitHubでサインインしてもっと見る",
	"reg_cli_title":       "CLIで使う",
	"reg_cli_search":      "# スキルを検索",
	"reg_cli_install":     "# スキルをインストール",

	// -- Dashboard --
	"dash_title":          "ダッシュボード &mdash; AES",
	"dash_h1":             "レジストリトークン",
	"dash_subtitle":       "トークンを使ってAESレジストリにスキルやテンプレートを公開できます。",
	"dash_th_name":        "名前",
	"dash_th_created":     "作成日",
	"dash_revoke":         "取り消し",
	"dash_revoke_prefix":  "トークンを取り消しますか: ",
	"dash_revoke_suffix":  "?",
	"dash_empty":          "トークンがまだありません。以下から作成してください。",
	"dash_create_title":   "新しいトークンを作成",
	"dash_token_label":    "トークン名",
	"dash_token_hint":     "英数字、ハイフン、アンダースコアが使用可能。GitHubユーザー名がプレフィックスとして付きます。",
	"dash_create_btn":     "トークンを作成",
	"dash_max_pre":        "トークンは最大",
	"dash_max_post":       "個までです。新しく作成するには既存のトークンを取り消してください。",
	"dash_usage_title":    "使い方",
	"dash_usage_set_tok":  "# トークンを設定",
	"dash_usage_set_url":  "# レジストリURLを設定",
	"dash_usage_pub_skill": "# スキルを公開",
	"dash_usage_pub_tmpl": "# テンプレートを公開",

	// -- Error page --
	"err_title":   "エラー &mdash; AES",
	"err_heading": "エラーが発生しました",
	"err_go_home": "ホームに戻る",

	// -- Token created page --
	"tc_title":   "トークン作成完了 &mdash; AES",
	"tc_loading": "トークンを有効化中",
	"tc_heading": "トークン作成完了",
	"tc_warning": "このトークンを今すぐコピーしてください。再表示されません。",
	"tc_copy":    "コピー",
	"tc_setup":   "環境を設定",
	"tc_back":    "ダッシュボードに戻る",
}
