import os
import sys
import ast
from pathlib import Path

# Add root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

def check_syntax(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        compile(content, file_path, 'exec')
        return None
    except SyntaxError as e:
        return f"SYNTAX ERROR: {e.filename}:{e.lineno} - {e.msg}"
    except Exception as e:
        return f"READ ERROR: {file_path} - {str(e)}"

def check_imports_exist(file_path):
    errors = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            root = ast.parse(f.read(), filename=file_path)
            
        for node in ast.walk(root):
            if isinstance(node, ast.ImportFrom):
                module = node.module
                if module and module.startswith('app'):
                    # Convert 'app.core.services' to 'app/core/services'
                    rel_path = module.replace('.', os.sep)
                    
                    # Check if it points to a directory (package) or file
                    possible_dir = os.path.join(ROOT_DIR, rel_path)
                    possible_file = os.path.join(ROOT_DIR, rel_path + ".py")
                    
                    if not os.path.exists(possible_dir) and not os.path.exists(possible_file):
                        # Try finding directory with __init__
                        if os.path.isdir(possible_dir) and os.path.exists(os.path.join(possible_dir, "__init__.py")):
                            continue
                        errors.append(f"IMPORT ERROR: Line {node.lineno} - Module '{module}' not found at '{rel_path}'")
                        
    except Exception:
        pass # Syntax error already caught
        
    return errors

def main():
    print(f"Starting Audit in: {ROOT_DIR}")
    print("-" * 50)
    
    total_files = 0
    syntax_errors = 0
    import_errors = 0
    
    for root, dirs, files in os.walk(ROOT_DIR):
        if "venv" in root or "__pycache__" in root or ".git" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                total_files += 1
                fullpath = os.path.join(root, file)
                relpath = os.path.relpath(fullpath, ROOT_DIR)
                
                # Check 1: Syntax
                syn_err = check_syntax(fullpath)
                if syn_err:
                    print(f"❌ {relpath}")
                    print(f"   {syn_err}")
                    syntax_errors += 1
                    continue # Skip import check if syntax fails
                
                # Check 2: Imports
                imp_errs = check_imports_exist(fullpath)
                if imp_errs:
                    print(f"⚠️ {relpath}")
                    for err in imp_errs:
                        print(f"   {err}")
                    import_errors += 1
                else:
                    # print(f"✅ {relpath}") # Silent success for cleaner output
                    pass

    print("-" * 50)
    print(f"Audit Complete. Scanned {total_files} files.")
    print(f"Syntax Errors: {syntax_errors}")
    print(f"Import Warnings: {import_errors}")
    
    if syntax_errors == 0 and import_errors == 0:
        print("\nSUCCESS: Codebase looks structurally sound.")
    else:
        print("\nATTENTION: Please fix the errors above.")

if __name__ == "__main__":
    main()
