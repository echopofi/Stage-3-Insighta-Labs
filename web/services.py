import httpx
import asyncio
import hashlib
import base64
import secrets
import re
from models import COUNTRY_MAP


def get_age_group(age: int) -> str:
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


def generate_code_verifier(length: int = 128) -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).rstrip(b'=').decode()


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


async def fetch_profile_data(name: str):
    urls = {
        "Genderize": f"https://api.genderize.io?name={name}",
        "Agify": f"https://api.agify.io?name={name}",
        "Nationalize": f"https://api.nationalize.io?name={name}"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            responses = await asyncio.gather(
                client.get(urls["Genderize"]),
                client.get(urls["Agify"]),
                client.get(urls["Nationalize"])
            )
        except (httpx.RequestError, httpx.TimeoutException):
            return "External API", None

        gen_data = responses[0].json()
        agi_data = responses[1].json()
        nat_data = responses[2].json()

        if not gen_data.get("gender") or gen_data.get("count") == 0:
            return "Genderize", None

        if agi_data.get("age") is None:
            return "Agify", None

        if not nat_data.get("country"):
            return "Nationalize", None

        top_country = max(nat_data["country"], key=lambda x: x["probability"])
        country_id = top_country["country_id"]
        country_name = COUNTRY_MAP.get(country_id, country_id)

        return None, {
            "gender": gen_data["gender"],
            "gender_probability": gen_data["probability"],
            "sample_size": gen_data["count"],
            "age": agi_data["age"],
            "age_group": get_age_group(agi_data["age"]),
            "country_id": country_id,
            "country_name": country_name,
            "country_probability": top_country["probability"],
        }


def parse_natural_language_query(q: str) -> dict:
    filters = {}
    q_lower = q.lower()

    gender_filter_applied = False
    if ("male" in q_lower or "males" in q_lower) and ("female" in q_lower or "females" in q_lower):
        gender_filter_applied = False
    elif "male" in q_lower or "males" in q_lower:
        filters["gender"] = "male"
        gender_filter_applied = True
    elif "female" in q_lower or "females" in q_lower:
        filters["gender"] = "female"
        gender_filter_applied = True

    if "young" in q_lower:
        filters["min_age"] = 16
        filters["max_age"] = 24
    elif "above" in q_lower:
        match = re.search(r"above\s*(\d+)", q_lower)
        if match:
            filters["min_age"] = int(match.group(1))
    elif "below" in q_lower:
        match = re.search(r"below\s*(\d+)", q_lower)
        if match:
            filters["max_age"] = int(match.group(1))

    query_words = set(q_lower.replace(",", " ").replace("from", " ").replace("of", " ").split())

    for country_code, country_name in COUNTRY_MAP.items():
        if country_code.lower() in query_words or country_name.lower() in query_words:
            filters["country_id"] = country_code
            break

    for ag in ["child", "teenager", "adult", "senior"]:
        if ag in query_words:
            filters["age_group"] = ag
            break

    return filters


def validate_query_keywords(q: str) -> bool:
    q_lower = q.lower()
    query_words = set(q_lower.replace(",", " ").replace("from", " ").replace("of", " ").split())
    
    valid_keywords = set()
    valid_keywords.update(["male", "males", "female", "females", "young", "above", "below", "child", "teenager", "adult", "senior"])
    valid_keywords.update([c.lower() for c in COUNTRY_MAP.keys()])
    valid_keywords.update([n.lower() for n in COUNTRY_MAP.values()])
    
    return bool(query_words.intersection(valid_keywords))