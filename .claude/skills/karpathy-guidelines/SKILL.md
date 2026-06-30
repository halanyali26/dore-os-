---
name: karpathy-guidelines
description: "Apply Karpathy's 4 LLM coding rules: think before coding, simplicity first, surgical changes, goal-driven execution. Use when coding, refactoring, or reviewing Dore OS pipeline code."
version: 1.0
---

# Karpathy's LLM Coding Guidelines

## Rule 1: Think Before Coding
Plan the approach before writing any code. Outline the architecture, data flow, and edge cases.

## Rule 2: Simplicity First
Start with the simplest implementation that works. Avoid premature abstraction. Add complexity only when proven necessary.

## Rule 3: Surgical Changes
Make minimal, targeted edits. Change only what needs changing. Never refactor unrelated code in the same pass.

## Rule 4: Goal-Driven Execution
Stay focused on the specific task. If a tangential issue arises, note it but don't fix it now. Complete the primary goal first.

## Application in Dore OS
- Pipeline changes: plan state transitions before coding
- Agent modifications: keep agents focused on single responsibility
- Dashboard updates: surgical CSS/JS changes only
