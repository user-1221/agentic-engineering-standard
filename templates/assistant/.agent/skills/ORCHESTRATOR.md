# Skill Orchestrator

## Pipeline

greeting -> (user message) -> route to skill or general response

## Decision Tree

On each message:
  |- Is greeting? -> greeting skill
  |- Is skill command? -> execute named skill
  \- General message -> conversational response
