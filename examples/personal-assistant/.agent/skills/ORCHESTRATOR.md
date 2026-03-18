# Skill Orchestrator

## Pipeline

greeting -> (user message) -> route to skill or general response

## Status Flow

idle -> processing -> responding -> idle

## Decision Tree

On each message:
  |- Is greeting? -> greeting skill
  |- Is skill command (e.g. /search)? -> execute named skill
  |- Matches auto-skill context? -> execute auto skill
  \- General message -> conversational response

## When to Stop

When the user explicitly ends the conversation or goes idle for >10 minutes.
