
# Script to fix indentation in assistant_service.py line 313
path = r"c:\Users\umut\OneDrive\Masaüstü\sesli asistan\app\core\services\assistant_service.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Line 313 (index 312) seems to be the issue
# Let's inspect lines around it
target_idn = 312

print(f"Original Line {target_idn+1}: {repr(lines[target_idn])}")
print(f"Previous Line {target_idn}: {repr(lines[target_idn-1])}")

# Fix indentation to match previous 'elif' (index 310 or 311)
# elif is at index 311 (line 312)
elif_line = lines[311]
indentation = elif_line[:elif_line.find("elif")]

print(f"Detected Indentation: {repr(indentation)}")

# Apply fix
lines[target_idn] = indentation + "else:\n"
# Also fix the following lines if they are over-indented
# The logger line below
lines[target_idn+1] = lines[target_idn+1].replace("                           ", "                         ", 1) # Reduce spaces
lines[target_idn+2] = lines[target_idn+2].replace("                           ", "                         ", 1)
lines[target_idn+3] = lines[target_idn+3].replace("                           ", "                         ", 1)

print(f"Fixed Line {target_idn+1}: {repr(lines[target_idn])}")

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("File corrected.")
