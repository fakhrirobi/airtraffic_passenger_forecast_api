FROM python:3.8.5 


WORKDIR /api 

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD [ "python", "main_api.py"]


