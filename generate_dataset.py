import csv
import random
from datetime import datetime

random.seed(42)

CATEGORIES = [
    ("Road & Infrastructure", "roads"),
    ("Water Supply", "water"),
    ("Drainage & Sewage", "drainage"),
    ("Sanitation", "sanitation"),
    ("Electricity", "electricity"),
    ("Street Lights", "streetlights"),
    ("Health & Hygiene", "health"),
    ("Animal Control", "animals"),
    ("Emergency", "emergency"),
    ("General", "general"),
]

LOCATIONS = [
    "near bus stop", "near school", "near hospital", "near market", "near temple",
    "in my street", "in our area", "near junction", "near bridge", "near park",
    "at main road", "in 2nd street", "behind the apartment", "near railway gate",
]
TIME_HINTS = [
    "since yesterday", "for 3 days", "for 1 week", "from last night", "after rain",
    "every morning", "daily", "for many days", "from last month", "since morning",
]
INTENSIFIERS = [
    "very severe", "getting worse", "urgent", "serious", "dangerous", "unbearable",
    "huge", "massive", "continuous", "frequent",
]

TEMPLATES = {
    "Road & Infrastructure": [
        "There is a {intensity} pothole {loc} {time}.",
        "Road surface is damaged {loc} {time}. Vehicles are struggling to pass.",
        "Broken footpath {loc} {time}. Pedestrians are getting hurt.",
        "Open manhole on the road {loc} {time}. Accident risk is high.",
        "Speed breaker damaged {loc} {time}. Causing traffic issues."
    ],
    "Water Supply": [
        "Water supply is not coming {loc} {time}.",
        "There is a water pipeline leak {loc} {time}.",
        "Low water pressure {loc} {time}.",
        "Dirty water is coming in tap {loc} {time}.",
        "Water overflow near pipeline {loc} {time}."
    ],
    "Drainage & Sewage": [
        "Drainage is blocked {loc} {time}. Water is overflowing.",
        "Sewage overflow {loc} {time}. Bad smell everywhere.",
        "Drain water stagnation {loc} {time}.",
        "Manhole overflow {loc} {time}.",
        "Drain cover broken {loc} {time}."
    ],
    "Sanitation": [
        "Garbage is not collected {loc} {time}.",
        "Waste dumped openly {loc} {time}.",
        "Dustbin overflowing {loc} {time}.",
        "Garbage burning smell {loc} {time}.",
        "Dead animal not removed {loc} {time}."
    ],
    "Electricity": [
        "Power cut {loc} {time}.",
        "Transformer sparking {loc} {time}.",
        "Voltage fluctuation {loc} {time}. Appliances are getting damaged.",
        "Electric pole wire loose {loc} {time}.",
        "Electricity not available {loc} {time}."
    ],
    "Street Lights": [
        "Street light not working {loc} {time}.",
        "Lamp post broken {loc} {time}.",
        "Street lights are off {loc} {time}. Unsafe at night.",
        "Flickering street light {loc} {time}.",
        "Multiple street lights damaged {loc} {time}."
    ],
    "Health & Hygiene": [
        "Mosquito problem is {intensity} {loc} {time}. Dengue risk.",
        "Stagnant water causing mosquitoes {loc} {time}.",
        "Public toilet is dirty {loc} {time}.",
        "Bad smell and hygiene issue {loc} {time}.",
        "Fever cases increasing due to mosquitoes {loc} {time}."
    ],
    "Animal Control": [
        "Stray dogs causing trouble {loc} {time}.",
        "Aggressive stray dog bite risk {loc} {time}.",
        "Cows blocking road {loc} {time}.",
        "Stray animals near school {loc} {time}.",
        "Dog barking and chasing vehicles {loc} {time}."
    ],
    "Emergency": [
        "Fire incident reported {loc} {time}. Need immediate help.",
        "Accident happened {loc} {time}. Ambulance required.",
        "Building collapse risk {loc} {time}. Please check urgently.",
        "Electrocution hazard {loc} {time}. Very dangerous.",
        "Gas leak smell {loc} {time}. Please respond fast."
    ],
    "General": [
        "Need help regarding civic issue {loc} {time}.",
        "Public issue needs attention {loc} {time}.",
        "Kindly check and resolve the issue {loc} {time}.",
        "Complaint about local problem {loc} {time}.",
        "Request immediate action {loc} {time}."
    ],
}

HIGH_TRIGGERS = [
    "accident", "fire", "collapse", "electrocution", "gas leak", "hospital",
    "dangerous", "bite risk", "open manhole", "sparking"
]


def infer_priority(text: str) -> str:
    t = text.lower()
    return "High" if any(k in t for k in HIGH_TRIGGERS) else "Medium"


def generate_one(category: str) -> str:
    template = random.choice(TEMPLATES[category])
    return template.format(
        loc=random.choice(LOCATIONS),
        time=random.choice(TIME_HINTS),
        intensity=random.choice(INTENSIFIERS),
    )


def make_dataset(n_rows: int = 5000, out_file: str = "dataset.csv"):

    per_cat = n_rows // len(CATEGORIES)
    extra = n_rows % len(CATEGORIES)

    rows = []
    for i, (cat, dept) in enumerate(CATEGORIES):
        count = per_cat + (1 if i < extra else 0)
        for _ in range(count):
            complaint = generate_one(cat)
            priority = infer_priority(complaint)
            rows.append([complaint, cat, priority, dept])

    random.shuffle(rows)

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["complaint", "category", "priority", "department"])
        writer.writerows(rows)

    print(f"✅ Generated {len(rows)} rows -> {out_file} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")


if __name__ == "__main__":
    make_dataset(5000, "dataset.csv")