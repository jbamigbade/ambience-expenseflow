with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for some IDs in the HTML content
import re
print("Searching for section IDs in HTML:")
sections = re.findall(r'id=["\'](section-[^"\']+)["\']', content)
for s in sections:
    print(f"  Section ID: {s}")

print("\nSearching for tab buttons:")
tabs = re.findall(r'class=["\']tab-btn[^"\']*["\'][^>]*id=["\']([^"\']+)["\']', content)
for t in tabs:
    print(f"  Tab Button: {t}")

print("\nSearching for modal IDs:")
modals = re.findall(r'id=["\'](modal-[^"\']+)["\']', content)
for m in modals:
    print(f"  Modal ID: {m}")
