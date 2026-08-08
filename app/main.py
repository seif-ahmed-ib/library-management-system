from fastapi import FastAPI

app = FastAPI(
    title="Library Management System API",
    description="Backend API for managing books and borrowing operations.",
    version="1.0.0",
)


@app.get("/", tags=["Health"])
def read_root() -> dict[str, str]:
    return {"message": "Library Management System API is running"}