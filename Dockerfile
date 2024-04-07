FROM python:3.10

COPY . /home/

RUN pip install mariadb discord python-dotenv requests

WORKDIR /home

CMD ["python", "-u", "./main.py"]

