FROM rapidsai/notebooks:26.08-cuda12-py3.12

RUN python -m pip install --no-cache-dir "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "pydantic>=2,<3"

WORKDIR /home/rapids/api
COPY app.py ./app.py

ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["app:app", "--host", "0.0.0.0", "--port", "8000"]
