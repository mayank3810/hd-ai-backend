FROM python:3.11.4

WORKDIR /code

COPY ./app /code/app
COPY .env ./.env
COPY ./requirements.txt ./code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r ./code/requirements.txt

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]