# Command: /setup

Review and customize the `.agent/` files for your personal assistant project.

## Phase 1: Review Configuration

1. Read `.agent/agent.yaml` — verify identity, model, channels, and heartbeat settings
2. Read `.agent/permissions.yaml` — review security boundaries
3. Check environment variables are documented and available

## Phase 2: Customize Identity

1. Update `identity.persona` with the desired personality and tone
2. Set `identity.name` and `identity.emoji` to personalize the agent
3. Fill in `identity.user_profile` with how the user wants to be addressed

## Phase 3: Configure Channels

1. For each messaging platform you want to use, set `enabled: true`
2. Ensure the corresponding bot token environment variable is set
3. Test connectivity with `openclaw gateway --dry-run`

## Phase 4: Verify

1. Run `aes validate` to check all files
2. Run `aes sync -t openclaw --dry-run` to preview the generated config
3. Run `aes sync -t openclaw` to generate the `.openclaw/` directory
