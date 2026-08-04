with open("web/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find line 1515 where </html> appears
cut_idx = -1
for i, line in enumerate(lines):
    if "</html>" in line and i > 1400:
        cut_idx = i
        break

if cut_idx != -1:
    clean_lines = lines[:cut_idx+1]
    with open("web/index.html", "w", encoding="utf-8") as f:
        f.writelines(clean_lines)
    print(f"Cleaned up web/index.html! Truncated at line {cut_idx+1}. New total lines:", len(clean_lines))
else:
    print("Could not find </html> cutoff line.")
