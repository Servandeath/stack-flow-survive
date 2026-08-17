from fastapi import FastAPI

app = FastAPI(title="stack-flow-survive")


@app.get("/")
def health_check():
    return {"status": "ok"}