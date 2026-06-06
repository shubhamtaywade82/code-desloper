import os
import re
import sys

# Common AI-generated smells and non-idiomatic patterns
SMELLS = [
    {
        "name": "Service Object Overkill (call/execute)",
        "pattern": r"(class|def).* (call|execute|perform)",
        "extensions": [".rb"],
        "description": "Small service objects might belong in the model or as a PORO."
    },
    {
        "name": "Wrapper Class (React/JS)",
        "pattern": r"class.*Manager|class.*Helper",
        "extensions": [".js", ".ts", ".tsx"],
        "description": "JS/React often prefers plain functions over wrapper classes."
    },
    {
        "name": "Excessive useMemo/useCallback",
        "pattern": r"useMemo\(|useCallback\(",
        "extensions": [".tsx", ".jsx"],
        "description": "Check if these are actually necessary or just AI-generated 'just in case' hooks."
    },
    {
        "name": "Explicit Return (Ruby)",
        "pattern": r"return\s",
        "extensions": [".rb"],
        "description": "Ruby has implicit returns; check if explicit return is non-idiomatic."
    },
    {
        "name": "TODO Scaffolding",
        "pattern": r"//\s*TODO|#\s*TODO",
        "extensions": [".rb", ".js", ".ts", ".tsx"],
        "description": "Placeholder code left by AI."
    },
    {
        "name": "Any Type (TS)",
        "pattern": r":\s*any",
        "extensions": [".ts", ".tsx"],
        "description": "Avoid 'any' type in TypeScript."
    },
    {
        "name": "ABC Overkill (Python)",
        "pattern": r"class.*\(ABC\):",
        "extensions": [".py"],
        "description": "Check if Abstract Base Class is really needed."
    },
    {
        "name": "Non-Idiomatic Loop (Python)",
        "pattern": r"range\(len\(",
        "extensions": [".py"],
        "description": "Use direct iteration or enumerate()."
    },
    {
        "name": "Premature Interface (Go)",
        "pattern": r"type.*interface\s*{",
        "extensions": [".go"],
        "description": "Ensure interface is needed for multiple implementations or mocking."
    }
]

def scan_file(file_path):
    results = []
    _, ext = os.path.splitext(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for smell in SMELLS:
                if ext in smell["extensions"]:
                    matches = re.finditer(smell["pattern"], content)
                    for match in matches:
                        line_no = content.count('\n', 0, match.start()) + 1
                        results.append({
                            "file": file_path,
                            "line": line_no,
                            "smell": smell["name"],
                            "description": smell["description"]
                        })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        
    return results

def main(root_dir):
    all_results = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if any(file.endswith(ext) for smell in SMELLS for ext in smell["extensions"]):
                file_path = os.path.join(root, file)
                all_results.extend(scan_file(file_path))
    
    if not all_results:
        print("No obvious smells detected!")
        return

    print(f"{'File':<40} | {'Line':<5} | {'Smell':<30}")
    print("-" * 80)
    for res in all_results:
        print(f"{res['file'][:40]:<40} | {res['line']:<5} | {res['smell']:<30}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    main(target)
