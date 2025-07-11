At the end of this message, I will explain my goal and ask for help.

Please follow the "Explore, Plan, Code, Test" workflow when you start.

# Explore
First, use parallel subagents to find and read all files that may be useful for implementing the change, either as examples or as edit targets. The subagents should return relevant file paths, and any other info that may be useful. You can use `gemini -p <prompt>` for Gemini AI which is good at very large files with its large context window.

# Plan
Next, think hard and write up a detailed implementation plan. Don't forget to include tests, and sphinx based inline documentation. Use your judgement as to what is necessary, given the standards of this repo.

If there are things you are not sure about, use parallel subagents to do some web research. They should only return useful information, no noise.

If there are things you still do not understand or questions you have for the user, pause here to ask them before continuing.

# Code
When you have a thorough implementation plan, you are ready to start writing code. Follow the style of the existing codebase, although the target should be aligned to the defaults in the `black` linter. Fix linter warnings that seem reasonable to you.

# Instructions

This code is a mess, both the code itself and the directory of files. Originally I wrote the python to
import highly structured json data from the 5e.tools website, for transforming into LaTeX documents
that match the style of the official D&D 5th edition books.

The python code worked for 75% of data, and I had some good output. I'm not sure it's very solid
anymore, as I haven't looked in many months and they have slowly improved their json data to add more
capabilities.

The workflow was something like

```shell
git clone https://github.com/5etools-mirror-3/5etools-src
cd 5e2pdf
./json2tex.py --no-images --add-items --add-creatures --book .../5etools-src/data/adventure/adventure-cos.json > adventure-cos.tex
xelatex adventure-cos.tex
```
The directory is a mess of all my test and work-in-progress documents. LaTeX is especially good at
making .aux files and such which pollutes the space even further.

There are two high level goals.
1. Clean up the directory and have scripted build processes that match the workflow described
2. Refactor the python code to improve use of objects, role seperation, loose coupling, etc.

I want to focus on #1 first, cleaning up the data. Have a good rummage around and understand what the
files are and how we should structure them.