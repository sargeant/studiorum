# Tag Resolution System Overhaul

> Current Issue: Regex-based parsing with 25+ tag types is becoming unmaintainable and error-prone.
>  Recommended Solution:
>  - Migrate to a formal parsing library like lark or pyparsing
>  - Define clear grammar for tag syntax
>  - Implement visitor pattern over Abstract Syntax Tree (AST)
>  - Benefits: Better error handling, easier extensibility, cleaner separation of parsing vs resolution

This might be important to know since I plan to add it later; I want to be able to print a full adventure, and anytime it uses a specific tag type (e.g., spell or item) I want to store that fact for later. In the appendix of the LaTeX document, I want to add descriptions of all the spells/items/creatures mentioned in the book. Don't try to implement that feature for now, I'm just raising it here in case it makes a different to the new tag system implementation. 


Use the TDD pattern to plan this. Discuss with Gemini at the plan stage to get a second 
opinion and revise your thinking if needed.
