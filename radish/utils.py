def tabulate(string, indent=2):
    return "\n".join(" " * indent + line for line in string.splitlines())
