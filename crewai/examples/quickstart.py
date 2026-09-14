"""Minimal direct-tool smoke test (no LLM, no Crew).

Calls each tool once so you can confirm your TINYFISH_API_KEY works.

    export TINYFISH_API_KEY="your_api_key_here"
    python examples/quickstart.py
"""

from crewai_tinyfish import TinyFishFetchTool, TinyFishSearchTool

if __name__ == "__main__":
    print("== Search ==")
    print(TinyFishSearchTool().run(query="TinyFish web agent", max_results=3))

    print("\n== Fetch ==")
    print(TinyFishFetchTool().run(urls=["https://www.tinyfish.ai/"], max_chars_per_url=400))
