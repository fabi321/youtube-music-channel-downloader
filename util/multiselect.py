def multiselect(greeting: str, prompt: str, selections: list[str]) -> int:
    while True:
        print(greeting)
        for i in range(len(selections)):
            print(f"{i+1}. {selections[i]}")
        res = input(prompt)
        if res.isdecimal():
            res: int = int(res)
            if 0 < res <= len(selections):
                return res - 1
            print(f"The number needs to be within 1 and {len(selections)}")
        else:
            print("Please only enter numbers")
