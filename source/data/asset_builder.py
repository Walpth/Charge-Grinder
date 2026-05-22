import json


from base_path import JSON_PATH, GEN_PATH
    

def generate_code():
    with open(JSON_PATH, "r") as f:
        data = json.load(f)

    lines = [
        "# ==========================================",
        "# AUTO-GENERATED FILE - DO NOT EDIT MANUALLY",
        "# Run asset_builder.py to update this file. ",
        "# ==========================================",
        "from source.engine.search_region import SearchRegion",
        "from source.engine.target import Target, MatchResult",
        "from .asset_library import AssetLibrary",
        ""
    ]

    for category, elements in data.items():
        lines.append(f"class {category}Elements:")
        lines.append(f"    def __init__(self, registry: AssetLibrary):")
        
        for name, props in elements.items():
            lines.append(f"        self.{name}: SearchRegion = registry.get('{category}', '{name}')")
        lines.append("")

    lines.append("class UIDatabase:")
    lines.append("    def __init__(self, registry: AssetLibrary):")
    lines.append("        self.point = Target(None, MatchResult(), registry.controller)")
    for category in data.keys():
        lines.append(f"        self.{category} = {category}Elements(registry)")

    with open(GEN_PATH, "w") as f:
        f.write("\n".join(lines))

    print("Successfully generated 'assets_generated.py'!")

if __name__ == "__main__":
    generate_code()