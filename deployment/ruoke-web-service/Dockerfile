FROM python:3.12.8-slim

RUN pip install -U pip
RUN pip install pipenv

WORKDIR /app
COPY [ "Pipfile", "Pipfile.lock", "./" ]

RUN pipenv install --system --deploy
# --system installs the packages into the system Python environment, not the virtual environment
# --deploy ensures that the installed packages match the Pipfile.lock exactly

COPY ["predict.py", "lin_reg.bin", "./"]
EXPOSE 9696
ENTRYPOINT ["gunicorn", "--bind=0.0.0.0:9696", "predict:app"]
# gunicorn is a Python WSGI HTTP Server for UNIX
# EXTRYPOINT specifies the command to run when the container starts