import json
import logging
import os

import dotenv

from Arknights import Arknights

dotenv.load_dotenv()

email = os.getenv("EMAIL")
dump_operators = os.getenv("DUMP_OPERATORS", "false").lower() == "true"
dump_planner = os.getenv("DUMP_PLANNER", "false").lower() == "true"

client = Arknights(
    email=email
)
client.login()
client_data = client.getSyncData()

if dump_operators:
    logging.info("Dumping operators...")
    with open("operator_list.json", "r") as f:
        old_operator_list = json.load(f)

    operator_list = {}
    for char_data in client_data["user"]["troop"]["chars"].values():
        operator_list.update({
            char_data["charId"]: {
                "class": "Medic",
                "favorite": False,
                "id": char_data["charId"],
                "level": char_data["level"],
                "name": char_data["charId"],
                "owned": True,
                "potential": char_data["potentialRank"] + 1,
                "promotion": char_data["evolvePhase"],
                "rarity": 1,
                "skillLevel": char_data["mainSkillLvl"],
                "skin": char_data["skin"],
                "mastery": [],
                "module": []
            }
        })

        if "@" in operator_list[char_data["charId"]]["skin"]:
            operator_list[char_data["charId"]]["skin"] = operator_list[char_data["charId"]]["skin"].replace("@", "_").replace("#", "%23")
        else:
            operator_list[char_data["charId"]]["skin"] = operator_list[char_data["charId"]]["skin"].replace("#1", "").replace("#2", "_2")

        if char_data["charId"] in old_operator_list:
            operator_list[char_data["charId"]]["class"] = old_operator_list[char_data["charId"]]["class"]
            operator_list[char_data["charId"]]["favorite"] = old_operator_list[char_data["charId"]]["favorite"]
            operator_list[char_data["charId"]]["name"] = old_operator_list[char_data["charId"]]["name"]
            operator_list[char_data["charId"]]["rarity"] = old_operator_list[char_data["charId"]]["rarity"]

        mastery_exists = any([skill_data["specializeLevel"] != 0 for skill_data in char_data["skills"]])
        if mastery_exists:
            for skill_data in char_data["skills"]:
                operator_list[char_data["charId"]]["mastery"].append(None if skill_data["specializeLevel"] == 0 else skill_data["specializeLevel"])

        module_exists = False
        if char_data["equip"]:
            for module_name, module_data in char_data["equip"].items():
                if module_name.startswith("uniequip_001"):
                    continue

                if module_data["locked"] != 1:
                    module_exists = True
                    break

        if module_exists:
            for module_name, module_data in char_data["equip"].items():
                if module_name.startswith("uniequip_001"):
                    continue

                operator_list[char_data["charId"]]["module"].append(None if module_data["locked"] == 1 else module_data["level"])

    sorted_operator_list = dict(sorted(operator_list.items(), key=lambda item: item[0].split("_")[1]))
    with open("new_operator_list.json", "w") as f:
        f.write(json.dumps(sorted_operator_list))

if dump_planner:
    logging.info("Dumping planner...")
    with open("planner.json") as f:
        planner_data = json.load(f)

    new_items = {
        "@type": "@penguin-statistics/planner/config",
        "items": [],
    }

    for item, count in client_data["user"]["inventory"].items():
        if item.isdigit() or item in ["mod_unlock_token", "mod_update_token_1", "mod_update_token_2"]:
            need = 0

            for index, material in enumerate(planner_data["items"]):
                if material["id"] == item:
                    need = material["need"]
                    break

            new_items["items"].append({
                "id": item,
                "have": count,
                "need": need
            })

    with open("new_planner.json", "w") as f:
        json.dump(new_items, f, indent=4)
