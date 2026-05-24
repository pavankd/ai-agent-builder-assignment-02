from graph import build_graph


def main():
    graph = build_graph()
    png_bytes = graph.get_graph().draw_mermaid_png()
    with open("graph.png", "wb") as f:
        f.write(png_bytes)
    print("Graph diagram saved to graph.png")


if __name__ == "__main__":
    main()
