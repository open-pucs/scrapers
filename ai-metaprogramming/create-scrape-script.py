from scrapegraphai.graphs import ScriptCreatorGraph

graph_config = {"llm": {...}, "library": "beautifulsoup4"}

script_creator_graph = ScriptCreatorGraph(
    prompt="Create a Python script to scrape the projects.",
    source="https://perinim.github.io/projects/",
    config=graph_config,
    schema=schema,
)

result = script_creator_graph.run()
print(result)
