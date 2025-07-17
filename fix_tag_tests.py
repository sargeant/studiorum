#!/usr/bin/env python3

import re

# Read the file
with open("tests/unit/test_tag_resolver.py", "r") as f:
    content = f.read()

# Pattern to match test methods that need tag_resolver
pattern = r"(\s+)(def test_[^(]+\(self, tag_resolver\):)"


# Replace with async version
def replace_func(match):
    indent = match.group(1)
    func_def = match.group(2)
    return f"{indent}@pytest.mark.asyncio\n{indent}async {func_def}"


content = re.sub(pattern, replace_func, content)

# Pattern to match tag_resolver usage in test bodies
pattern2 = r"(\s+)(text = .*?\n\s+result = tag_resolver\.process_text\(text\))"


def replace_usage(match):
    indent = match.group(1)
    old_usage = match.group(2)
    # Extract the text line and result line
    lines = old_usage.split("\n")
    text_line = lines[0]
    lines[1].strip()

    return f"{indent}resolver = await tag_resolver\n{indent}{text_line}\n{indent}result = resolver.process_text(text)"


content = re.sub(pattern2, replace_usage, content, flags=re.DOTALL)

# Write back
with open("tests/unit/test_tag_resolver.py", "w") as f:
    f.write(content)

print("Fixed tag resolver tests")
