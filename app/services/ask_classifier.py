def classify_question(question: str) -> str:
    print(f"🟣 ask_classifier: Klassificerer question: '{question}'")
    q = question.lower()
    print(f"🟣 ask_classifier: Lowercase question: '{q}'")
    
    # Mere omfattende sammenligning detektion
    compare_keywords = [
        "sammenlign", "forskel", "difference", "compare", "versus", "vs", "vs.",
        "kontra", "mod", "bedre", "værre", "bedst", "værst", "fordel", "ulempe",
        "forskellig", "ligner", "ligheder", "ulighed", "alternativer", "valg",
        "hvilken er bedst", "hvad er bedst", "hvem er bedst", "preferred",
        "anbefal", "recommendation", "vælg", "choose", "option", "muligheder"
    ]
    
    analyse_keywords = [
        "analys", "vurder", "evaluate", "assess", "undersøg", "examine", "review",
        "gennemgang", "analysis", "evaluation", "assessment", "undersøgelse",
        "rapport", "redegørelse", "konklusion", "opsummering", "oversigt"
    ]
    
    # Check for sammenligning
    if any(keyword in q for keyword in compare_keywords):
        print("🟣 ask_classifier: Klassificeret som 'compare' (sammenligning)")
        return "compare"
    
    # Check for analyse
    if any(keyword in q for keyword in analyse_keywords):
        print("🟣 ask_classifier: Klassificeret som 'analyse'")
        return "analyse"
    
    # Specifikke sammenligning patterns
    if any(pattern in q for pattern in [
        "mellem", "and", "eller", "kontra", " vs ", " vs.", " v. "
    ]):
        print("🟣 ask_classifier: Klassificeret som 'compare' (pattern match)")
        return "compare"
    
    # Hvis der nævnes flere selskaber, antag sammenligning
    companies = ["tryg", "topdanmark", "cna", "hdi", "alka", "if", "codan", "gjensidige"]
    mentioned_companies = [comp for comp in companies if comp in q]
    if len(mentioned_companies) > 1:
        print(f"🟣 ask_classifier: Klassificeret som 'compare' (flere selskaber: {mentioned_companies})")
        return "compare"
    
    print("🟣 ask_classifier: Klassificeret som 'query' (default)")
    return "query"
