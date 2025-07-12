# Querying Content in 5e2pdf

This document outlines the research and recommendation for implementing a powerful query language in the `5e2pdf` CLI.

## Goal

The goal is to allow users to formulate complex queries to filter the content from the `Omnidexer`. This will enable commands like:

*   `5e2pdf convert --query "item.type == 'beast' and item.cr <= 6"`
*   `5e2pdf convert --query "item.school == 'evocation' and 'fire' in item.name"`

The query language should be both powerful and easy for users to learn and use, with a preference for an intuitive, Python-like syntax.

## Research Findings

Several options were investigated, each with its own trade-offs:

### 1. Hand-rolled Filtering with Typer Options

*   **How it works:** Implement a series of Typer options like `--type`, `--challenge-rating-max`, `--name-contains`, etc.
*   **Pros:** Simple to implement for basic cases. No new dependencies.
*   **Cons:** Becomes unwieldy and complex very quickly. Combining filters with `AND`/`OR` logic is difficult to implement and use. Does not scale well.

### 2. `jmespath`

*   **How it works:** A powerful, standardized query language for JSON-like data.
*   **Pros:** Powerful, safe, and a well-established standard for querying JSON.
*   **Cons:** The syntax is not Pythonic and would require users to learn a new query language. It also requires converting our Pydantic objects to dictionaries before every query, adding a small performance overhead.

### 3. `eval()`-based solution

*   **How it works:** Take a string and run it through Python's `eval()` function.
*   **Pros:** Extremely powerful, as it's raw Python.
*   **Cons:** **EXTREMELY DANGEROUS.** Poses a massive security risk and will not be considered.

### 4. `asteval`

*   **How it works:** A library that provides a secure and restricted environment for evaluating Python expressions. It parses the expression into an Abstract Syntax Tree (AST) and safely executes it with a controlled symbol table.
*   **Pros:**
    *   **Intuitive Python Syntax:** Queries are valid Python expressions, making them easy to write and understand (e.g., `item.cr < 5 and item.name.startswith('A')`).
    *   **Works with Objects:** Can operate directly on our Pydantic objects without needing to convert them to dictionaries.
    *   **Safe:** Designed as a secure alternative to `eval()`. We have full control over the functions and names available to the query.
    *   **Flexible:** Can easily expose safe, custom helper functions to the query environment (e.g., a `slugify()` function).
*   **Cons:**
    *   Requires careful implementation to ensure the evaluation environment is properly sandboxed.
    *   Being so close to Python might create user expectations for features that are intentionally disabled for security.

## Recommendation

The recommended approach is to use the **`asteval`** library.

It provides the most intuitive and user-friendly query experience by leveraging a familiar, Python-like syntax. This aligns perfectly with the project's goal of being easy to use. The ability to query against the Pydantic objects directly is a significant advantage, simplifying the implementation and improving performance.

While safety is a consideration, `asteval` is designed for this purpose. The implementation will create a tightly sandboxed environment, exposing only the object being evaluated (`item`) and a minimal set of safe, built-in functions.

### Example Usage

With `asteval`, a query to find all beasts with a challenge rating of 6 or lower would look like this:

```
"item.type == 'beast' and item.cr <= 6"
```

A query to find all evocation spells with "fire" in the name:

```
"item.school == 'E' and 'fire' in item.name.lower()"
```
*(Assuming `item.school` is 'E' for Evocation)*

This syntax is immediately familiar to anyone with basic Python knowledge and is expressive enough for complex filtering needs.

### Next Steps

1.  Add `asteval` as a project dependency.
2.  Create a new `query` module in `src/core` that will be responsible for taking a query string and a list of objects, and returning the filtered list using a safely configured `asteval` interpreter.
3.  Integrate this query module into the relevant CLI commands (e.g., a new `convert` command or by adding a `--query` flag).