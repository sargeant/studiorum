# Claude

Please follow the "Explore, Plan, Code, Test" workflow when you start.

## Explore
First, use parallel subagents to find and read all files that may be useful for implementing the change, either as examples or as edit targets. The subagents should return relevant file paths, and any other info that may be useful. You can use `gemini -p <prompt>` for Gemini AI which is good at very large files with its large context window.

## Plan
Next, think hard and write up a detailed implementation plan. Don't forget to include tests, and sphinx based inline documentation. Use your judgement as to what is necessary, given the standards of this repo.

If there are things you are not sure about, use parallel subagents to do some web research. They should only return useful information, no noise.

If there are things you still do not understand or questions you have for the user, pause here to ask them before continuing.

## Code
When you have a thorough implementation plan, you are ready to start writing code. Follow the style of the existing codebase, although the target should be aligned to the defaults in the `black` linter. Fix linter warnings that seem reasonable to you.

## Test
Use parallel subagents to run tests, and make sure they all pass.

If your testing shows problems, go back to the planning stage and think ultra-hard.