import json
import ollama
from parse_data import load_items, get_unclaimed_items, save_result

def build_prompt(description, available_items):
    system_prompt = """You are a highly analytical lost-and-found assistant.
Rules for the Model:
- The model must use ONLY the given JSON items.
- Not all the details of an item must match to be a possible match.
- Only JSON must be returned, with exactly the following structure:
{
    "matches": ["ITEM_ID"],
    "confidence": "LOW"
}
- "matches" contains all the possible matches' IDs. If there is no match, return an empty list: [].
- "confidence" measures how confident you are about the matches. It must be exactly one of: LOW, MEDIUM, HIGH.
- Output strictly valid JSON and nothing else. Do not wrap it in markdown code blocks."""

    items_json_str = json.dumps(available_items, indent=2)
    user_prompt = f"""Available unclaimed items:
{items_json_str}

Description of the lost item: {description}"""

    return system_prompt, user_prompt


def ask_qwen(system_prompt, user_prompt):
    response = ollama.chat(
        model='qwen3:8b',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
    )
    return response['message']['content']


def parse_response(response_text):
    text = response_text.strip()
    
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
        
    if text.endswith("```"):
        text = text[:-3]
        
    text = text.strip()
    return json.loads(text)


def validate_result(result, available_items):
    if not isinstance(result, dict):
        return False
    
    if "matches" not in result or "confidence" not in result:
        return False
        
    if not isinstance(result["matches"], list):
        return False
        
    if result["confidence"] not in ["LOW", "MEDIUM", "HIGH"]:
        return False
        
    valid_ids = {item["id"] for item in available_items}
    for match_id in result["matches"]:
        if match_id not in valid_ids:
            return False
            
    return True


def display_matches(result, available_items):
    print("MATCH RESULT")
    print("-" * 50)
    print(f"Confidence: {result.get('confidence', 'LOW')}\n")
    
    matches = result.get("matches", [])
    
    if not matches:
        print("No possible matches found.\n")
    else:
        print("Possible matches:\n")
        item_lookup = {item["id"]: item for item in available_items}
        
        for match_id in matches:
            item = item_lookup.get(match_id)
            if item:
                print(f"ID: {item['id']}")
                print(f"Item: {item['item']}")
                print(f"Color: {item['color']}")
                print(f"Location: {item['location']}")
                print(f"Date found: {item.get('date', 'Unknown')}\n")

    print("Result saved to output/match_result.json\n")


def main():
    print("CAMPUS LOST-AND-FOUND ASSISTANT")
    print("=" * 50)
    
    description = input("\nDescribe the item you lost: ").strip()
    print("\nSearching for possible matches...\n")
    
    items = load_items("found_items.json")
    unclaimed_items = get_unclaimed_items(items)
    
    sys_prompt, usr_prompt = build_prompt(description, unclaimed_items)
    
    try:
        response_text = ask_qwen(sys_prompt, usr_prompt)
        
        result = parse_response(response_text)
        
        if not validate_result(result, unclaimed_items):
            print("Error: The model returned an invalid JSON structure or invalid IDs.")
            return

        display_matches(result, unclaimed_items)
        save_result(result, "output/match_result.json")
        
    except Exception as e:
        print(f"An error occurred while communicating with the model: {e}")


if __name__ == "__main__":
    main()