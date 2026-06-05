import json
import urllib.request

queries = [
    "Can I receive visitors on weekends?",
    "Can my lawyer visit me privately?",
    "Can I make phone calls?",
    "Can I send mail?",
    "What if I need urgent medical help?",
    "How do I file a complaint?",
    "How do I appeal a disciplinary sanction?",
    "Can I attend religious services?",
    "Can I borrow books from the library?",
    "Can I buy hygiene products from the canteen?",
    "Can I request a transfer?",
    "Can I join educational programs?"
]

for q in queries:
    payload = json.dumps(
        {"query": q, "top_k": 3},
        ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:8000/retrieve",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    print("\n==============================")
    print("ORIGINAL:", result["original_query"])
    print("TRANSLATED:", result["translated_query"])

    for i, r in enumerate(result["results"], start=1):
        print(f"{i}. {r['text']}")
        print(f"   SCORE: {r['score']}")
        print(f"   PAGE: {r['page']}")
        print(f"   SOURCE: {r['source']}")