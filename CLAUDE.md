# Claude

This is a python project to parse the json data files of D&D content from 5e.tools, then transform into LaTeX for PDF output.

## Important notes

- This project is managed by uv
- always use `head` to limit the number of lines of output you see from testing, in case it explodes. 50 is usually a good start, but use your judgement. Because the default content has thousands of entries to load, single validation errors can generate 30k lines of debug output.
- Please follow the TDD workflow described below anytime I ask for TDD or test-driven.

## Gemini

When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive context window. Use `gemini -p <prompt>` when:

- Analyzing entire codebases or large directories
- Comparing multiple large files
- Reading binary files such as PDFs or anything else you doesn't support directly
- Need to understand project-wide patterns or architecture
- Checking for the presence of certain coding patterns across the entire codebase

## Test Driven Development (TDD) workflow

This workflow has the following stages;

- Explore
- Plan
- Write Tests
- Code
- Validate Tests

## Explore

First, use parallel subagents to find and read all files that may be useful for implementing the change, either as examples or as edit targets. The subagents should return relevant file paths, and any other info that may be useful. Don't forget to try using gemini if you have a large file or codebase to analyse.

### Plan

Next, think hard and write up a detailed implementation plan. Don't forget to include tests, and sphinx based inline documentation. Use your judgement as to what is necessary, given the standards of this repo.

If there are things you are not sure about, use parallel subagents to do some web research. They should only return useful information, no noise.

If there are things you still do not understand or questions you have for the user, pause here to ask them before continuing.

### Tests

Make sure unit tests are added first with the expected behaviour of new additions. If you are changing how a feature operates, make sure the tests are present and correct.

Use parallel subagents to run tests, and make sure they all pass.

If your testing shows problems, go back to the plan stage and think ultra-hard.

### Code

When you have a thorough implementation plan and unit tests, you are ready to start writing code. Follow the style of the existing codebase, although the target should be aligned to the defaults in the `black` linter. Fix linter warnings that seem reasonable to you.
