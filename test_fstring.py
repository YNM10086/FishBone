def test():
    return f"""async function loadHistory() {
    try {
        const x = 1;
    }
}"""
import ast; ast.parse(open("test_fstring.py").read()); print("OK")
